import os
import pytest
import fakeredis

os.environ.setdefault('md5_key', 'test_secret')
os.environ.setdefault('ADMIN_API_KEY', 'test_admin_key')

import main


@pytest.fixture
def fake_redis():
    server = fakeredis.FakeServer()
    return fakeredis.FakeRedis(server=server, decode_responses=True)


@pytest.fixture
def app(fake_redis):
    main.init_redis(fake_redis)
    main.app.config['TESTING'] = True
    yield main.app


@pytest.fixture
def client(app):
    return app.test_client()
