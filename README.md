# Visitor Badge

Count visitors for your GitHub, Blog or Portfolio Site in just one line markdown code or one api call

![visitor badge](https://visitor-badge.one9x.com/badge?page_id=visitor-badge)


## How to use?

If you know how to add picture in markdown or image in html, then you are good to go.

#### Markdown

```md
![visitors](https://visitor-badge.example.net/badge?page_id={page.id}&left_color=red&right_color=green)
```

#### HTML

```html
<img src="https://visitor-badge.example.net/badge?page_id={page.id}&left_color=red&right_color=green" />
```

#### API

```bash
curl -X GET "http://visitor-badge.example.net/count?page_id={page.id}"

// output: {"value": 100}
```

### Options
| Params          | Required | Default | Description                                                  |
| --------------- | -------- | ------- | ------------------------------------------------------------ |
| `page_id`       | Required | null    | Unique string to best represent your page                    |
| `namespace`     | Optional | default | Unique key to group all your pages and avoid conflict with others (max 10 chars) |
| `read`          | Optional | false   | Only return existing count, don't increment                   |
| `unique`        | Optional | false   | Only count unique visitors within a given window as set by timeframe param. Uses cookie-based dedup with server-side fingerprint fallback for cross-origin embeds |
| `timeframe`     | Optional | 600     | Time window (in seconds) for unique visitor dedup. Range: 60-86400 (1 min to 24 hrs) |
| *`left_color`   | Optional | #595959 | Left side color of the badge                                  |
| *`left_text`    | Optional | visitor | Left side text of the badge                                   |
| *`right_color`  | Optional | #1283c3 | Right side color of the badge                                 |

**Note:** * options only applied for path `/badge`

### Bot Filtering

Common bots (Googlebot, bingbot, crawlers, etc.) are automatically detected and excluded from visitor counts. You can customize the bot detection patterns via the `BOT_UA_PATTERNS` environment variable (comma-separated regex patterns).

### Unique Visitor Counting

When `unique=true`, the service uses a two-layer dedup strategy:
1. **Cookie-based** (primary): Works for direct browser visits. Requires HTTPS for cross-origin badge embeds (SameSite=None).
2. **Fingerprint-based** (fallback): For cross-origin `<img>` embeds where cookies aren't available. Uses a hash of IP prefix + browser family + time bucket.

The `/count` endpoint returns a `method` field when `unique=true` indicating which dedup method was used: `"cookie"` or `"fingerprint"`.

## Admin API

Manage namespace-level configuration via the admin API. All endpoints require an `X-API-Key` header matching the `ADMIN_API_KEY` environment variable. Rate limited to 10 requests/minute per IP.

```bash
# List all namespace configs
curl -H "X-API-Key: YOUR_KEY" http://localhost:5000/admin/namespaces

# Get namespace config
curl -H "X-API-Key: YOUR_KEY" http://localhost:5000/admin/namespace/myns

# Set namespace badge defaults
curl -X PUT -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
  -d '{"badge_defaults": {"left_color": "blue", "left_text": "hits"}}' \
  http://localhost:5000/admin/namespace/myns

# Delete namespace config
curl -X DELETE -H "X-API-Key: YOUR_KEY" http://localhost:5000/admin/namespace/myns
```

Namespace badge defaults are applied when a badge request includes `namespace=myns`. User query params still override namespace defaults.

## Health Check

```bash
curl http://localhost:5000/health/backup
// output: {"status": "healthy", "last_backup": "2026-03-29T12:00:00Z"}
```

Returns `200` if backup ran within the last 2 hours, `503` if stale or unknown.

## Self-Hosting

### Docker Compose

```bash
git clone https://github.com/ramank775/visitor-badge.git
cd visitor-badge
```

Create a `.env` file:
```env
md5_key=your_secret_key
ADMIN_API_KEY=your_admin_key
```

```bash
docker-compose up -d
```

This starts three services:
- **redis**: Data store
- **visitor-badge**: The badge service on port 5000
- **backup**: Hourly Redis backups with 48hr hourly + 30-day daily retention

### Environment Variables

| Variable          | Required | Default   | Description                                      |
| ----------------- | -------- | --------- | ------------------------------------------------ |
| `md5_key`         | Yes      | -         | Secret key for page ID hashing                   |
| `redis_host`      | No       | 127.0.0.1 | Redis host                                       |
| `redis_port`      | No       | 6379      | Redis port                                       |
| `redis_db`        | No       | 0         | Redis database number                            |
| `ADMIN_API_KEY`   | No       | -         | API key for admin endpoints (disabled if not set) |
| `BOT_UA_PATTERNS` | No       | (built-in)| Comma-separated regex patterns for bot detection |
| `host`            | No       | 127.0.0.1 | App listen host                                  |
| `port`            | No       | 5000      | App listen port                                  |

### Backup & Restore

Backups run automatically every hour via the backup sidecar container. Snapshots are stored in the `backup-data` Docker volume.

To restore from a backup:
```bash
./backup/restore.sh /path/to/backups/daily/dump-20260329.rdb
```

**Note:** With Docker named volumes, you may need to use `docker cp` to place the RDB file into the Redis container's data directory.

## Public Servers
- URL: https://visitor-badge.one9x.com

    Free: Yes

    Please be aware that this server is hosted on a homelab environment, which may result in occasional downtime or data loss. To minimize the risk of data loss, nightly data snapshots are taken at 12:00 AM IST.

## What's next?

- **Data federation**: Allow independent servers to sync visitor data for shared namespaces
- **Real-time badges**: Show "X people viewing now" instead of total count
- **Active viewers**: Track live presence per page

Have something in mind? [Just tell me...](https://github.com/ramank775/visitor-badge/issues/new)

#### Fork From
> jwenjian: [https://github.com/jwenjian/visitor-badge](https://github.com/jwenjian/visitor-badge)
