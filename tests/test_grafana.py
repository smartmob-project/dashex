# -*- coding: utf-8 -*-


import json
import mock
import os.path
import pytest
import requests.exceptions

from dashex import grafana_wait
from dashex.__main__ import main


def loadfile(path):
    """Load a file from disk."""
    with open(path, 'rb') as stream:
        return stream.read().decode('utf-8')


def loadjson(path):
    """Load a JSON document from disk."""
    return json.loads(loadfile(path))


def savefile(path, data):
    """Save a file to disk."""
    with open(path, 'wb') as stream:
        stream.write(data.encode('utf-8'))


def savejson(path, data):
    """Save a JSON document to disk."""
    savefile(path, json.dumps(data))


def test_grafana_pull(influxdb, grafana, fs_sandbox):
    """``dashex grafana-pull`` saves files to disk."""

    # Given an InfluxDB database.
    influxdb.create_database('dbmetrics')

    # Given a Grafana data source that pulls from InfluxDB.
    grafana.create_influxdb_datasource(
        'redis', influxdb.url, 'dbmetrics',
    )

    # Given a Grafana dashboard.
    grafana.create_dashboard('Redis Command Activity')

    # When we download the configuration.
    main(['grafana-pull',
          '-i', grafana.url,
          '-u', grafana.username,
          '-p', grafana.password])

    # Then we should see a Grafana configuration on disk.
    assert os.path.isdir('grafana/datasources')
    assert os.path.isdir('grafana/dashboards')

    # And the datasource file should be valid JSON.
    document = loadjson('grafana/datasources/redis.json')
    print(json.dumps(document, indent=2, sort_keys=True))

    # And the datasource description should be in the JSON document.
    assert document['type'] == 'influxdb'
    assert document['name'] == 'redis'
    assert document['url'] == influxdb.url
    assert document['database'] == 'dbmetrics'
    assert document['access'] == 'proxy'
    assert document['basicAuth'] is False
    assert document['user'] == ''
    assert document['password'] == ''
    assert document['jsonData'] == {}

    # But the IDs should not be preserved (may already be assigned in
    # destination instance).
    assert 'id' not in document
    assert 'orgId' not in document
    assert 'typeLogoUrl' not in document

    # And the dashboard file should be valid JSON.
    document = loadjson('grafana/dashboards/redis-command-activity.json')
    print(json.dumps(document, indent=2, sort_keys=True))

    # And the dashboard contents should be in the JSON document.
    assert 'dashboard' in document
    for field in ('schemaVersion', 'title', 'version', 'timezone', 'tags'):
        assert field in document['dashboard']

    # But the dashboard ID should not be preserved (ID may already be assigned
    # in destination instance).
    assert 'id' not in document['dashboard']

    # And the dashboard metadata should be in the JSON document.
    assert 'meta' in document
    for field in ('slug', 'created', 'createdBy',
                  'updated', 'updatedBy', 'expires'):
        assert field in document['meta']


def test_pull_search_non_dashboard_result(make_http_service):
    """Dashboard enum skips non-dashboard things in search results."""

    def list_datasources():
        return []

    def search():
        return [
            {
                'type': 'SOMETHING UNEXPECTED!',
            },
        ]

    routes = {
        'GET': {
            '/api/datasources': list_datasources,
            '/api/search': search,
        },
    }

    with make_http_service(routes) as url:
        # When we download the configuration.
        main(['grafana-pull',
              '-i', url,
              '-u', 'admin',
              '-p', 'admin'])


def test_grafana_push(influxdb, grafana, fs_sandbox):
    """``dashex grafana-push`` loads files from disk."""

    # Given an InfluxDB database.
    influxdb.create_database('dbmetrics')

    # Given a Grafana configuration on disk.
    os.mkdir('grafana')
    os.mkdir('grafana/datasources')
    savejson('grafana/datasources/mysql.json', {
        'name': 'mysql',
        'type': 'influxdb',
        'url': influxdb.url,
        'database': 'dbmetrics',
        'access': 'proxy',
        'basicAuth': False,
        'user': '',
        'password': '',
    })
    os.mkdir('grafana/dashboards')
    savejson('grafana/dashboards/mysql-command-activity.json', {
        'dashboard': {
            'schemaVersion': 6,
            'title': 'MySQL Command Activity',
            'version': 0,
            'timezone': 'browser',
            'tags': [],
        },
        'meta': {
            # Rest doesn't matter, will not be uploaded.
            'slug': 'mysql-command-activity',
        },
    })

    assert os.path.isdir('grafana/datasources')
    assert os.path.exists('grafana/datasources/mysql.json')
    assert os.path.isdir('grafana/dashboards')
    assert os.path.exists('grafana/dashboards/mysql-command-activity.json')

    # When we upload the configuration.
    main(['grafana-push',
          '-i', grafana.url,
          '-u', grafana.username,
          '-p', grafana.password])

    # When we should be able to upload it again (and update contents).
    main(['grafana-push',
          '-i', grafana.url,
          '-u', grafana.username,
          '-p', grafana.password])


def test_grafana_push_version_conflict(influxdb, grafana, fs_sandbox):
    """``dashex grafana-push`` skips updates with version conflicts."""

    # Given an InfluxDB database.
    influxdb.create_database('dbmetrics')

    # Given a Grafana configuration on disk.
    os.mkdir('grafana')
    os.mkdir('grafana/datasources')
    savejson('grafana/datasources/mysql.json', {
        'name': 'mysql',
        'type': 'influxdb',
        'url': influxdb.url,
        'database': 'dbmetrics',
        'access': 'proxy',
        'basicAuth': False,
        'user': '',
        'password': '',
    })
    os.mkdir('grafana/dashboards')

    # Given the dashboard is at a given version.
    savejson('grafana/dashboards/mysql-command-activity.json', {
        'dashboard': {
            'schemaVersion': 6,
            'title': 'MySQL Command Activity',
            'version': 3,
            'timezone': 'browser',
            'tags': [],
        },
        'meta': {
            # Rest doesn't matter, will not be uploaded.
            'slug': 'mysql-command-activity',
        },
    })
    main(['grafana-push',
          '-i', grafana.url,
          '-u', grafana.username,
          '-p', grafana.password])

    # When we upload an older version (e.g. because it was modified by someone
    # else in the meantime), it should be ignored.
    savejson('grafana/dashboards/mysql-command-activity.json', {
        'dashboard': {
            'schemaVersion': 6,
            'title': 'MySQL Command Activity',
            'version': 2,
            'timezone': 'browser',
            'tags': [],
        },
        'meta': {
            # Rest doesn't matter, will not be uploaded.
            'slug': 'mysql-command-activity',
        },
    })
    main(['grafana-push',
          '-i', grafana.url,
          '-u', grafana.username,
          '-p', grafana.password])


def test_grafana_push_failure(influxdb, grafana, fs_sandbox):
    """``dashex grafana-push`` reports unexpected errors."""

    # Given an InfluxDB database.
    influxdb.create_database('dbmetrics')

    # Given a Grafana configuration on disk.
    os.mkdir('grafana')
    os.mkdir('grafana/datasources')
    savejson('grafana/datasources/mysql.json', {
        'name': 'mysql',
        'type': 'influxdb',
        'url': influxdb.url,
        'database': 'dbmetrics',
        'access': 'proxy',
        'basicAuth': False,
        'user': '',
        'password': '',
    })
    os.mkdir('grafana/dashboards')

    class MockHTTP503(object):
        @property
        def status_code(self):
            return 503

    e = requests.exceptions.HTTPError(response=MockHTTP503())

    real_post = requests.post

    def mock_post(*args, **kwds):
        if args[0].endswith('/api/dashboards/db'):
            raise e
        return real_post(*args, **kwds)

    # When we upload the dashboard.
    savejson('grafana/dashboards/mysql-command-activity.json', {
        'dashboard': {
            'schemaVersion': 6,
            'title': 'MySQL Command Activity',
            'version': 0,
            'timezone': 'browser',
            'tags': [],
        },
        'meta': {
            # Rest doesn't matter, will not be uploaded.
            'slug': 'mysql-command-activity',
        },
    })
    with mock.patch('requests.post') as post:
        post.side_effect = mock_post
        with pytest.raises(requests.exceptions.HTTPError) as exc:
            main(['grafana-push',
                  '-i', grafana.url,
                  '-u', grafana.username,
                  '-p', grafana.password])
        assert exc.value is e


def test_grafana_wait():
    """We can wait until the service binds to its socket."""

    class MockRequest(object):
        def raise_for_status(self):
            return

    with mock.patch('time.sleep') as sleep:
        with mock.patch('requests.get') as get:
            get.side_effect = [
                requests.exceptions.ConnectionError(),
                requests.exceptions.ConnectionError(),
                MockRequest(),
            ]
            grafana_wait(
                'http://grafana.example.org',
                username='admin', password='admin',
            )

    assert sleep.mock_calls == [
        mock.call(1.0),
        mock.call(1.0),
    ]
    assert get.call_count == 3


def test_grafana_wait_unexpected_exception():
    """Unexpected exceptions are forwarded."""

    e = ValueError()

    class MockRequest(object):
        def raise_for_status(self):
            raise e

    with pytest.raises(ValueError) as exc:
        with mock.patch('requests.get') as get:
            get.side_effect = [
                MockRequest(),
            ]
            grafana_wait(
                'http://grafana.example.org',
                username='admin', password='admin',
            )

    assert exc.value is e


def test_grafana_wait_timeout():
    """Do not wait indefinitely (in unsupervised execution context)."""

    mock_clock = mock.MagicMock()
    mock_clock.side_effect = [
        0.0,  # reference time.
        0.0,  # on 1st iteration (intial condition).
        1.0,  # on 2nd iteration.
        2.0,  # on 3rd iteration.
        3.0,  # on 4th iteration (denied due to timeout).
    ]

    with mock.patch('time.sleep') as sleep:
        with mock.patch('requests.get') as get:
            get.side_effect = [
                requests.exceptions.ConnectionError(),
                requests.exceptions.ConnectionError(),
                requests.exceptions.ConnectionError(),
            ]
            with pytest.raises(Exception) as exc:
                grafana_wait(
                    'http://grafana.example.org',
                    username='admin', password='admin',
                    timeout=2.5, clock=mock_clock,
                )
            assert str(exc.value) == 'Grafana is unresponsive at this time.'

    assert sleep.mock_calls == [
        mock.call(1.0),
        mock.call(1.0),
        mock.call(1.0),
    ]
    assert get.call_count == 3
