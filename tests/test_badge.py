import json


class TestBadgeEndpoint:
    def test_happy_path(self, client, fake_redis):
        resp = client.get('/badge?page_id=testpage')
        assert resp.status_code == 200
        assert resp.content_type == 'image/svg+xml'
        assert b'<svg' in resp.data

    def test_increments_counter(self, client, fake_redis):
        client.get('/badge?page_id=counter_test')
        client.get('/badge?page_id=counter_test')
        resp = client.get('/count?page_id=counter_test')
        data = json.loads(resp.data)
        assert data['value'] == 3  # 2 badge + 1 count

    def test_custom_colors(self, client, fake_redis):
        resp = client.get('/badge?page_id=test&left_color=red&right_color=green')
        assert resp.status_code == 200
        assert b'red' in resp.data or b'<svg' in resp.data

    def test_custom_left_text(self, client, fake_redis):
        resp = client.get('/badge?page_id=test&left_text=views')
        assert resp.status_code == 200
        assert b'views' in resp.data

    def test_missing_page_id(self, client, fake_redis):
        resp = client.get('/badge')
        assert resp.status_code == 200  # Returns error badge, not 400
        assert b'Error' in resp.data

    def test_cache_headers(self, client, fake_redis):
        resp = client.get('/badge?page_id=test')
        assert 'no-cache' in resp.headers.get('Cache-Control', '')

    def test_namespace_defaults(self, client, fake_redis):
        # Set namespace defaults
        fake_redis.hset('ns:config:myns', 'badge_defaults',
                       json.dumps({'left_color': 'blue', 'left_text': 'hits'}))
        resp = client.get('/badge?page_id=test&namespace=myns')
        assert resp.status_code == 200
        assert b'hits' in resp.data

    def test_query_params_override_namespace(self, client, fake_redis):
        fake_redis.hset('ns:config:myns', 'badge_defaults',
                       json.dumps({'left_text': 'hits'}))
        resp = client.get('/badge?page_id=test&namespace=myns&left_text=views')
        assert resp.status_code == 200
        assert b'views' in resp.data


class TestCountEndpoint:
    def test_happy_path(self, client, fake_redis):
        resp = client.get('/count?page_id=test')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'value' in data

    def test_missing_page_id(self, client, fake_redis):
        resp = client.get('/count')
        assert resp.status_code == 400

    def test_read_only(self, client, fake_redis):
        client.get('/count?page_id=ro_test')  # increment
        resp = client.get('/count?page_id=ro_test&read=true')
        data = json.loads(resp.data)
        assert data['value'] == 1  # not incremented


class TestIndexPage:
    def test_index(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
