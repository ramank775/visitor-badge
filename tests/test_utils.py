import os
import time
from unittest.mock import patch

os.environ.setdefault('md5_key', 'test_secret')

from main import format_number, is_bot, compute_visitor_hash, get_timeframe


class TestFormatNumber:
    def test_small_number(self):
        assert format_number(42) == '42'

    def test_hundreds(self):
        assert format_number(999) == '999'

    def test_thousands(self):
        result = format_number(1500)
        assert 'K' in result

    def test_millions(self):
        result = format_number(2500000)
        assert 'M' in result

    def test_exact_thousand(self):
        result = format_number(1000)
        assert 'K' in result

    def test_zero(self):
        assert format_number(0) == '0'


class TestIsBot:
    def test_googlebot(self):
        assert is_bot('Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)') is True

    def test_bingbot(self):
        assert is_bot('Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)') is True

    def test_normal_browser(self):
        assert is_bot('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36') is False

    def test_empty_ua(self):
        assert is_bot('') is False

    def test_none_ua(self):
        assert is_bot(None) is False

    def test_crawler(self):
        assert is_bot('MyCustomCrawler/1.0') is True

    def test_spider(self):
        assert is_bot('WebSpider/3.0') is True


class TestComputeVisitorHash:
    def test_deterministic(self):
        h1 = compute_visitor_hash('192.168.1.100', 'Mozilla/5.0 Chrome/131', 600)
        h2 = compute_visitor_hash('192.168.1.100', 'Mozilla/5.0 Chrome/131', 600)
        assert h1 == h2

    def test_ipv4_prefix(self):
        # Same /24 prefix should produce same hash
        h1 = compute_visitor_hash('192.168.1.100', 'Mozilla/5.0 Chrome/131', 600)
        h2 = compute_visitor_hash('192.168.1.200', 'Mozilla/5.0 Chrome/131', 600)
        assert h1 == h2

    def test_different_ip_prefix(self):
        h1 = compute_visitor_hash('192.168.1.100', 'Mozilla/5.0 Chrome/131', 600)
        h2 = compute_visitor_hash('10.0.0.100', 'Mozilla/5.0 Chrome/131', 600)
        assert h1 != h2

    def test_ipv6_prefix(self):
        h1 = compute_visitor_hash('2001:db8:1234:5678::1', 'Chrome', 600)
        h2 = compute_visitor_hash('2001:db8:1234:9999::1', 'Chrome', 600)
        assert h1 == h2  # Same /48

    def test_malformed_ua_fallback(self):
        # Should not raise, falls back to raw UA
        h = compute_visitor_hash('192.168.1.1', '', 600)
        assert len(h) == 16

    def test_hash_length(self):
        h = compute_visitor_hash('1.2.3.4', 'Chrome', 600)
        assert len(h) == 16


class TestGetTimeframe:
    def test_default(self, app):
        with app.test_request_context('/badge?page_id=test'):
            assert get_timeframe() == 600

    def test_custom(self, app):
        with app.test_request_context('/badge?page_id=test&timeframe=300'):
            assert get_timeframe() == 300

    def test_clamp_low(self, app):
        with app.test_request_context('/badge?page_id=test&timeframe=0'):
            assert get_timeframe() == 60

    def test_clamp_high(self, app):
        with app.test_request_context('/badge?page_id=test&timeframe=999999'):
            assert get_timeframe() == 86400
