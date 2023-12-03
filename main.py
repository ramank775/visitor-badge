import datetime

from flask import Flask, Response, request, render_template, jsonify
from pybadges import badge
from hashlib import md5
from os import environ
from dotenv import find_dotenv, load_dotenv
import redis

load_dotenv(find_dotenv())

app = Flask(__name__)
redis_conn = None

def format_number(num):
    """
    Format a number using K for thousands, M for millions, etc.
    """
    num = float(num)
    suffixes = ['', 'K', 'M', 'B', 'T']
    suffix_index = 0

    while num >= 1000 and suffix_index < len(suffixes) - 1:
        num /= 1000.0
        suffix_index += 1

    formatted_num = '{:.2f}{}'.format(num, suffixes[suffix_index])
    return formatted_num.rstrip('0').rstrip('.')

def incr_counter(key):
    try:
        return redis_conn.incr(key)
    except Exception as e:
        return None

def get_count(key):
    try:
        val = redis_conn.get(key)
        if val is None:
            return 0
        return int(val)
    except Exception as e:
        return None

def get_or_increment_count(key, readonly=False) -> (int | None):
    if readonly:
        return get_count(key)
    return incr_counter(key)

def get_requested_count() -> (int | None):
    key = identity_request_source()
    readonly = readonly_request()
    return get_or_increment_count(key, readonly=readonly)


def invalid_count_resp(err_msg) -> Response:
    """
    Return a svg badge with error info when cannot process repo_id param from request
    :return: A response with invalid request badge
    """
    svg = badge(left_text="Error", right_text=err_msg)
    expiry_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)

    headers = {'Cache-Control': 'no-cache,max-age=0',
               'Expires': expiry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")}

    return Response(response=svg, content_type="image/svg+xml", headers=headers)

@app.route("/badge")
def visitor_svg() -> Response:
    """
    Return a svg badge with latest visitor count of 'Referer' header value

    :return: A svg badge with latest visitor count
    """
    try:
        count = get_requested_count()
    except Exception as e:
        return invalid_count_resp(e)
    if count is None:
        return invalid_count_resp('unable to fetch stats')
    # get left color, right color and left text
    left_color = '#595959'
    if request.args.get('left_color') is not None:
        left_color = request.args.get("left_color")

    right_color = '#1283c3'
    if request.args.get("right_color") is not None:
        right_color = request.args.get("right_color")
    
    left_text = 'visitor'
    if request.args.get('left_text') is not None:
        left_text =  request.args.get("left_text", default="visitors")
    
    formatted_count = format_number(count)

    svg = badge(left_text=left_text, right_text=str(formatted_count),
                left_color=str(left_color), right_color=str(right_color))

    expiry_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)

    headers = {'Cache-Control': 'no-cache,max-age=0,no-store,s-maxage=0,proxy-revalidate',
               'Expires': expiry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")}

    return Response(response=svg, content_type="image/svg+xml", headers=headers)

@app.route('/count')
def visitor_count() -> Response:
    """
    Return the latest visitor count of 'Referrer' 
    """
    try:
        count = get_requested_count()
        return jsonify({'value': count})
    except Exception as e:
        return jsonify({'error':str(e)}), 400

@app.route("/index.html")
@app.route("/index")
@app.route("/")
def index() -> Response:
    return render_template('index.html')

@app.after_request
def handle_response(resp: Response) -> Response:
    if has_unique_flag() and not readonly_request():
        key = identity_request_source()
        cookie_name = get_unique_tracking_cookie(key)
        timeframe = request.args.get('timeframe', type=int)
        if timeframe is None:
            timeframe = 600
        resp.set_cookie(
            cookie_name, 
            '1', 
            max_age=timeframe, 
            httponly=True,
            secure=True, 
            samesite='None'
        )
    return resp

def get_unique_tracking_cookie(key)->str:
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
    m.update(environ.get('md5_key').encode('utf-8'))
    digest = m.hexdigest()
    return f"{namespace}:{digest}"

def readonly_request()-> bool:
    readonly = request.args.get('read', False, type=bool)
    if readonly:
        return True
    unique = has_unique_flag()
    if unique:
        key = identity_request_source()
        cookie_name = get_unique_tracking_cookie(key)
        cookie = request.cookies.get(cookie_name, default='', type=str)
        return cookie is not None and len(cookie)
    return False

def has_unique_flag():
    unique = request.args.get('unique', False, type=bool)
    return unique

if __name__ == '__main__':
    redis_host = environ.get('redis_host', '127.0.0.1')
    redis_port = environ.get('redis_port', 6379)
    redis_db = environ.get('redis_db', 0)
    redis_conn = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
    host = environ.get('host', '127.0.0.1')
    port = environ.get('port', 5000)
    app.run(host=host, port=port)
