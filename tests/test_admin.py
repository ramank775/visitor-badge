import json
import os


ADMIN_KEY = os.environ.get('ADMIN_API_KEY', 'test_admin_key')


class TestAdminAuth:
    def test_valid_key(self, client, fake_redis):
        resp = client.get('/admin/namespaces',
                         headers={'X-API-Key': ADMIN_KEY})
        assert resp.status_code == 200

    def test_missing_key(self, client, fake_redis):
        resp = client.get('/admin/namespaces')
        assert resp.status_code == 401

    def test_wrong_key(self, client, fake_redis):
        resp = client.get('/admin/namespaces',
                         headers={'X-API-Key': 'wrong_key'})
        assert resp.status_code == 401

    def test_no_admin_key_configured(self, client, fake_redis, monkeypatch):
        monkeypatch.delenv('ADMIN_API_KEY', raising=False)
        resp = client.get('/admin/namespaces',
                         headers={'X-API-Key': 'anything'})
        assert resp.status_code == 401


class TestAdminRateLimit:
    def test_rate_limit_exceeded(self, client, fake_redis):
        for i in range(10):
            resp = client.get('/admin/namespaces',
                             headers={'X-API-Key': ADMIN_KEY})
            assert resp.status_code == 200

        resp = client.get('/admin/namespaces',
                         headers={'X-API-Key': ADMIN_KEY})
        assert resp.status_code == 429


class TestAdminNamespaceCRUD:
    def test_list_empty(self, client, fake_redis):
        resp = client.get('/admin/namespaces',
                         headers={'X-API-Key': ADMIN_KEY})
        data = json.loads(resp.data)
        assert data['namespaces'] == []

    def test_create_and_get(self, client, fake_redis):
        # Create
        resp = client.put('/admin/namespace/test',
                         headers={'X-API-Key': ADMIN_KEY,
                                  'Content-Type': 'application/json'},
                         data=json.dumps({
                             'badge_defaults': {'left_color': 'blue', 'left_text': 'hits'}
                         }))
        assert resp.status_code == 200

        # Get
        resp = client.get('/admin/namespace/test',
                         headers={'X-API-Key': ADMIN_KEY})
        data = json.loads(resp.data)
        assert data['namespace'] == 'test'
        defaults = json.loads(data['config']['badge_defaults'])
        assert defaults['left_color'] == 'blue'

    def test_list_after_create(self, client, fake_redis):
        client.put('/admin/namespace/ns1',
                  headers={'X-API-Key': ADMIN_KEY,
                           'Content-Type': 'application/json'},
                  data=json.dumps({'badge_defaults': {'left_text': 'views'}}))

        resp = client.get('/admin/namespaces',
                         headers={'X-API-Key': ADMIN_KEY})
        data = json.loads(resp.data)
        assert len(data['namespaces']) == 1
        assert data['namespaces'][0]['namespace'] == 'ns1'

    def test_delete(self, client, fake_redis):
        client.put('/admin/namespace/del_test',
                  headers={'X-API-Key': ADMIN_KEY,
                           'Content-Type': 'application/json'},
                  data=json.dumps({'badge_defaults': {}}))

        resp = client.delete('/admin/namespace/del_test',
                            headers={'X-API-Key': ADMIN_KEY})
        assert resp.status_code == 200

        resp = client.get('/admin/namespace/del_test',
                         headers={'X-API-Key': ADMIN_KEY})
        assert resp.status_code == 404

    def test_get_nonexistent(self, client, fake_redis):
        resp = client.get('/admin/namespace/nope',
                         headers={'X-API-Key': ADMIN_KEY})
        assert resp.status_code == 404


class TestAdminNamespaceValidation:
    def test_namespace_too_long(self, client, fake_redis):
        resp = client.put('/admin/namespace/this_is_way_too_long',
                         headers={'X-API-Key': ADMIN_KEY,
                                  'Content-Type': 'application/json'},
                         data=json.dumps({'badge_defaults': {}}))
        assert resp.status_code == 400

    def test_invalid_json(self, client, fake_redis):
        resp = client.put('/admin/namespace/test',
                         headers={'X-API-Key': ADMIN_KEY,
                                  'Content-Type': 'application/json'},
                         data='not json')
        assert resp.status_code == 400
