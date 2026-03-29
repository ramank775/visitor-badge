import json
from datetime import datetime, timezone, timedelta


class TestBackupHealth:
    def test_healthy(self, client, fake_redis):
        now = datetime.now(timezone.utc)
        fake_redis.set('backup:last_success', now.strftime('%Y-%m-%dT%H:%M:%SZ'))
        resp = client.get('/health/backup')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['status'] == 'healthy'

    def test_stale_backup(self, client, fake_redis):
        old = datetime.now(timezone.utc) - timedelta(hours=3)
        fake_redis.set('backup:last_success', old.strftime('%Y-%m-%dT%H:%M:%SZ'))
        resp = client.get('/health/backup')
        assert resp.status_code == 503
        data = json.loads(resp.data)
        assert data['status'] == 'unhealthy'

    def test_no_backup_recorded(self, client, fake_redis):
        resp = client.get('/health/backup')
        assert resp.status_code == 503
        data = json.loads(resp.data)
        assert data['status'] == 'unknown'

    def test_boundary_exactly_2_hours(self, client, fake_redis):
        boundary = datetime.now(timezone.utc) - timedelta(hours=2, seconds=1)
        fake_redis.set('backup:last_success', boundary.strftime('%Y-%m-%dT%H:%M:%SZ'))
        resp = client.get('/health/backup')
        assert resp.status_code == 503
