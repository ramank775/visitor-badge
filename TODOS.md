# TODOS

## ProxyFix for reverse proxy IP forwarding
- **What:** Add Flask ProxyFix middleware for X-Forwarded-For/X-Real-IP support
- **Why:** Without this, fingerprint dedup and admin rate limiting use proxy IP, not client IP
- **Context:** One-line addition (`app.wsgi_app = ProxyFix(app.wsgi_app)`). Should pair with HTTPS/reverse proxy setup.
- **Depends on:** HTTPS reverse proxy configuration
