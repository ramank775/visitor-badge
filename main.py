import datetime
import hmac
import hashlib
import json
import re
import time
from functools import wraps

from flask import Flask, Response, request, render_template, jsonify, g
from pybadges import badge
from hashlib import md5
from os import environ
from dotenv import find_dotenv, load_dotenv
import redis
from ua_parser import user_agent_parser

load_dotenv(find_dotenv())

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024  # 16KB max request body

redis_conn = None


def init_redis(redis_instance=None):
    global redis_conn
    if redis_instance is not None:
        redis_conn = redis_instance
        return
    redis_host = environ.get('redis_host', '127.0.0.1')
    redis_port = environ.get('redis_port', 6379)
    redis_db = environ.get('redis_db', 0)
    redis_conn = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)


# --- Bot Detection ---

BOT_PATTERNS = [re.compile(p, re.I) for p in
    environ.get('BOT_UA_PATTERNS',
        'bot,crawl,spider,slurp,mediapartners,facebookexternalhit,linkedinbot,twitterbot,whatsapp,telegram,discord'
    ).split(',')]


def is_bot(ua_string):
    return any(p.search(ua_string or '') for p in BOT_PATTERNS)


# --- Visitor Fingerprint ---

def compute_visitor_hash(ip, ua_string, timeframe):
    # IP prefix: /24 for IPv4, /48 for IPv6
    if ':' in ip:
        ip_prefix = ':'.join(ip.split(':')[:3])
    else:
        ip_prefix = '.'.join(ip.split('.')[:3])

    # Normalized UA with fallback on parse failure
    try:
        parsed = user_agent_parser.Parse(ua_string or '')
        ua_family = parsed['user_agent']['family'].lower()
        ua_major = parsed['user_agent'].get('major', '0') or '0'
        normalized_ua = f"{ua_family}{ua_major}"
    except Exception:
        normalized_ua = (ua_string or 'unknown')[:50].lower()

    # Time bucket aligned to timeframe
    time_bucket = str(int(time.time()) // timeframe * timeframe)

    msg = f"{ip_prefix}:{normalized_ua}:{time_bucket}"
    return hmac.new(environ.get('md5_key', '').encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]


def get_timeframe():
    tf = request.args.get('timeframe', 600, type=int)
    return max(60, min(tf, 86400))  # clamp 1min-24hr


# --- Number Formatting ---

def format_number(num):
    num = float(num)
    suffixes = ['', 'K', 'M', 'B', 'T']
    suffix_index = 0

    while num >= 1000 and suffix_index < len(suffixes) - 1:
        num /= 1000.0
        suffix_index += 1

    formatted_num = '{:.2f}{}'.format(num, suffixes[suffix_index])
    return formatted_num.rstrip('0').rstrip('.')


# --- Redis Counter Operations ---

def incr_counter(key):
    try:
        return redis_conn.incr(key)
    except Exception:
        return None


def get_count(key):
    try:
        val = redis_conn.get(key)
        if val is None:
            return 0
        return int(val)
    except Exception:
        return None


def get_or_increment_count(key, readonly=False):
    if readonly:
        return get_count(key)
    return incr_counter(key)


def get_requested_count():
    key = identity_request_source()
    # Bot check: never increment for bots
    if is_bot(request.headers.get('User-Agent', '')):
        g.dedup_method = 'bot'
        return get_count(key)
    readonly = readonly_request()
    return get_or_increment_count(key, readonly=readonly)


# --- Badge/Error Responses ---

def invalid_count_resp(err_msg) -> Response:
    svg = badge(left_text="Error", right_text=str(err_msg))
    expiry_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    headers = {'Cache-Control': 'no-cache,max-age=0',
               'Expires': expiry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")}
    return Response(response=svg, content_type="image/svg+xml", headers=headers)


def get_namespace_defaults(namespace):
    try:
        config = redis_conn.hgetall(f'ns:config:{namespace}')
        if config and 'badge_defaults' in config:
            return json.loads(config['badge_defaults'])
    except Exception:
        pass
    return {}


# --- Routes ---

@app.route("/badge")
def visitor_svg() -> Response:
    try:
        count = get_requested_count()
    except Exception as e:
        return invalid_count_resp(e)
    if count is None:
        return invalid_count_resp('unable to fetch stats')

    # Get namespace for defaults lookup
    namespace = request.args.get('namespace', 'default')
    ns_defaults = get_namespace_defaults(namespace)

    # Apply defaults: namespace defaults < hardcoded defaults < query params
    left_color = ns_defaults.get('left_color', '#595959')
    if request.args.get('left_color') is not None:
        left_color = request.args.get('left_color')

    right_color = ns_defaults.get('right_color', '#1283c3')
    if request.args.get('right_color') is not None:
        right_color = request.args.get('right_color')

    left_text = ns_defaults.get('left_text', 'visitor')
    if request.args.get('left_text') is not None:
        left_text = request.args.get('left_text', default='visitors')

    formatted_count = format_number(count)

    try:
        svg = badge(left_text=left_text, right_text=str(formatted_count),
                    left_color=str(left_color), right_color=str(right_color))
    except Exception:
        svg = badge(left_text=left_text, right_text=str(formatted_count),
                    left_color='#595959', right_color='#1283c3')

    expiry_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    headers = {'Cache-Control': 'no-cache,max-age=0,no-store,s-maxage=0,proxy-revalidate',
               'Expires': expiry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")}

    return Response(response=svg, content_type="image/svg+xml", headers=headers)


@app.route('/count')
def visitor_count() -> Response:
    try:
        count = get_requested_count()
        resp = {'value': count}
        if has_unique_flag() and hasattr(g, 'dedup_method'):
            resp['method'] = g.dedup_method
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route("/index.html")
@app.route("/index")
@app.route("/")
def index() -> Response:
    return render_template('index.html')


# --- Unique Visitor Tracking ---

@app.after_request
def handle_response(resp: Response) -> Response:
    try:
        if has_unique_flag() and not getattr(g, 'is_readonly', False):
            key = identity_request_source()
            cookie_name = get_unique_tracking_cookie(key)
            timeframe = get_timeframe()
            resp.set_cookie(
                cookie_name,
                '1',
                max_age=timeframe,
                httponly=True,
                secure=True,
                samesite='None'
            )
    except Exception:
        pass
    return resp


def get_unique_tracking_cookie(key) -> str:
    return f'__uq_{key}'


def identity_request_source() -> str:
    page_id = request.args.get('page_id')
    if page_id is None or not len(page_id):
        raise Exception('Missing required param: page_id')
    namespace = request.args.get('namespace')
    if namespace is None:
        namespace = 'default'
    if not len(namespace):
        raise Exception('param: namespace cannot be null or empty')
    if len(namespace) > 10:
        raise Exception('param: namespace max possible length 10')
    m = md5(page_id.encode('utf-8'))
    m.update(environ.get('md5_key', '').encode('utf-8'))
    digest = m.hexdigest()
    return f"{namespace}:{digest}"


def readonly_request() -> bool:
    readonly = request.args.get('read', False, type=bool)
    if readonly:
        g.is_readonly = True
        g.dedup_method = None
        return True

    unique = has_unique_flag()
    if unique:
        try:
            key = identity_request_source()
        except Exception:
            return False

        # Cookie-based dedup (primary)
        cookie_name = get_unique_tracking_cookie(key)
        cookie = request.cookies.get(cookie_name, default='', type=str)
        if cookie:
            g.is_readonly = True
            g.dedup_method = 'cookie'
            return True

        # Fingerprint-based dedup (fallback for cross-origin img embeds)
        timeframe = get_timeframe()
        ip = request.remote_addr or '0.0.0.0'
        ua = request.headers.get('User-Agent', '')
        visitor_hash = compute_visitor_hash(ip, ua, timeframe)

        # Extract digest from key (key is "namespace:digest")
        parts = key.split(':', 1)
        ns = parts[0] if len(parts) > 1 else 'default'
        digest = parts[1] if len(parts) > 1 else parts[0]

        seen_key = f"seen:{ns}:{digest}:{visitor_hash}"
        try:
            # Atomic: SET NX EX returns True if key was set (new visitor), None if already exists
            result = redis_conn.set(seen_key, '1', nx=True, ex=timeframe)
            if result is None:
                # Key already existed, this is a duplicate
                g.is_readonly = True
                g.dedup_method = 'fingerprint'
                return True
            else:
                # New visitor, allow increment
                g.dedup_method = 'fingerprint'
                return False
        except Exception:
            # Redis error, allow increment as fallback
            g.dedup_method = 'fingerprint'
            return False

    return False


def has_unique_flag():
    return request.args.get('unique', False, type=bool)


# --- Admin API ---

def validate_namespace(ns):
    if not ns or len(ns) == 0:
        return 'namespace cannot be empty'
    if len(ns) > 10:
        return 'namespace max possible length 10'
    return None


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        admin_key = environ.get('ADMIN_API_KEY')
        if not admin_key or api_key != admin_key:
            return jsonify({'error': 'unauthorized'}), 401
        # Rate limit: 10/min per IP
        try:
            rate_key = f"ratelimit:admin:{request.remote_addr}"
            count = redis_conn.incr(rate_key)
            if count == 1:
                redis_conn.expire(rate_key, 60)
            if count > 10:
                return jsonify({'error': 'rate limited'}), 429
        except Exception:
            pass  # Allow request if rate limiting fails
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/namespaces', methods=['GET'])
@require_admin
def admin_list_namespaces():
    try:
        namespaces = []
        cursor = 0
        while True:
            cursor, keys = redis_conn.scan(cursor, match='ns:config:*', count=100)
            for key in keys:
                ns = key.replace('ns:config:', '', 1)
                config = redis_conn.hgetall(key)
                namespaces.append({'namespace': ns, 'config': config})
            if cursor == 0:
                break
        return jsonify({'namespaces': namespaces})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/namespace/<ns>', methods=['GET'])
@require_admin
def admin_get_namespace(ns):
    try:
        config = redis_conn.hgetall(f'ns:config:{ns}')
        if not config:
            return jsonify({'error': 'namespace not found'}), 404
        return jsonify({'namespace': ns, 'config': config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/namespace/<ns>', methods=['PUT'])
@require_admin
def admin_set_namespace(ns):
    err = validate_namespace(ns)
    if err:
        return jsonify({'error': err}), 400
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({'error': 'invalid JSON body'}), 400
        # Store badge_defaults as JSON string
        if 'badge_defaults' in data:
            redis_conn.hset(f'ns:config:{ns}', 'badge_defaults', json.dumps(data['badge_defaults']))
        return jsonify({'namespace': ns, 'status': 'updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/namespace/<ns>', methods=['DELETE'])
@require_admin
def admin_delete_namespace(ns):
    try:
        redis_conn.delete(f'ns:config:{ns}')
        return jsonify({'namespace': ns, 'status': 'deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Health Check ---

@app.route('/health/backup')
def backup_health():
    try:
        last = redis_conn.get('backup:last_success')
        if last is None:
            return jsonify({'status': 'unknown', 'message': 'no backup recorded'}), 503
        last_dt = datetime.datetime.fromisoformat(last.replace('Z', '+00:00'))
        if datetime.datetime.now(datetime.timezone.utc) - last_dt > datetime.timedelta(hours=2):
            return jsonify({'status': 'unhealthy', 'last_backup': last}), 503
        return jsonify({'status': 'healthy', 'last_backup': last})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- App Entry Point ---

if __name__ == '__main__':
    init_redis()
    host = environ.get('host', '127.0.0.1')
    port = environ.get('port', 5000)
    app.run(host=host, port=port)
