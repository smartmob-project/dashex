# -*- coding: utf-8 -*-


from __future__ import print_function

import json
import os
import pytest
import requests
import requests.exceptions
import threading

try:
    # py3
    from http.server import (
        BaseHTTPRequestHandler,
        HTTPServer,
    )
except ImportError:
    # py2
    from BaseHTTPServer import (
        BaseHTTPRequestHandler,
        HTTPServer,
    )

from contextlib import contextmanager

try:
    # py3
    from urllib.parse import urljoin
except ImportError:
    # py2
    from urlparse import urljoin


@pytest.fixture(scope='function')
def fs_sandbox(tmpdir):
    """Move into a temporary folder while the test runs."""

    old_dir = os.getcwd()
    new_dir = tmpdir

    # Move into the temporary folder.
    os.chdir(str(new_dir))

    # Let the test run.
    yield

    # Move back into the originl folder.
    os.chdir(old_dir)


class InfluxDB(object):
    """Low-level InfluxDB client (automate HTTP requests)."""

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        return self._url

    def responsive(self):
        """Check if InfluxDB is responsive."""
        print('InfluxDB: ping...')
        rep = requests.get(urljoin(self.url, 'ping'))
        rep.raise_for_status()
        return True

    def cleanup(self):
        """Ensure InfluxDB is empty to prevent test cross-contamination."""
        print('InfluxDB: cleaning up...')
        for name in self.show_databases():
            print('InfluxDB: deleting database "%s".' % (name,))
            self.drop_database(name)

    def query(self, text):
        """Execute a query."""
        rep = requests.get(urljoin(self.url, 'query'), params={'q': text})
        rep.raise_for_status()
        return rep.json()['results']

    def create_database(self, name):
        """Create a database."""
        print('InfluxDB: creating database "%s".' % (name,))
        rep = requests.post(
            urljoin(self.url, 'query'),
            params={
                'q': 'CREATE DATABASE %s' % (name,),
            },
        )
        rep.raise_for_status()
        return rep.json()['results']

    def show_databases(self):
        output = self.query('SHOW DATABASES')
        output = output[0]['series'][0]
        if 'values' not in output:
            return []
        return output['values'][0]

    def drop_database(self, name):
        """Delete a database."""
        rep = requests.post(
            urljoin(self.url, 'query'),
            params={
                'q': 'DROP DATABASE %s' % (name,),
            },
        )
        rep.raise_for_status()
        return rep.json()['results']


@pytest.fixture(scope='session')
def influxdb_service(docker_ip, docker_services):
    """Wait until InfluxDB is responsive, return URL."""

    # Get the URL to InfluxDB.
    url = 'http://%s:%d' % (
        docker_ip,
        docker_services.port_for('influxdb', 8086),
    )
    print('Influx DB: URL=', url)
    service = InfluxDB(url)

    # Wait until InfluxDB is responsive.
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1,
        check=service.responsive,
    )
    print('InfluxDB: responsive!')

    # Ensure the first test starts clean.
    service.cleanup()

    # OK, it's ready to use now.
    return service


@pytest.fixture(scope='function')
def influxdb(influxdb_service):
    """Return URL, ensure InfluxDB is clean after the test."""

    # Let the test run.
    yield influxdb_service

    # Erase anything leftover by the test.
    influxdb_service.cleanup()


class Grafana(object):
    """Low-level Grafana client (automate HTTP requests)."""

    def __init__(self, url, username, password):
        self._url = url
        self._username = username
        self._password = password

    @property
    def url(self):
        return self._url

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    def responsive(self):
        """Check if Grafana is responsive."""
        print('Grafana: pinging...')
        try:
            rep = requests.get(self.url)
        except requests.exceptions.ConnectionError:
            return False
        rep.raise_for_status()
        return True

    def cleanup(self):
        """Ensure Grafana is empty to prevent test cross-contamination."""
        print('Grafana: cleaning up...')
        for slug in self.list_dashboards():
            print('Grafana: deleting dashboard "%s".' % (slug,))
            self.delete_dashboard(slug)
        for name in self.list_datasources():
            print('Grafana: deleting datasource "%s".' % (name,))
            self.delete_datasource(name)

    def list_datasources(self):
        """List all existing data sources."""
        rep = requests.get(
            urljoin(self.url, 'api/datasources'),
            auth=(self._username, self._password),
        )
        rep.raise_for_status()
        for result in rep.json():
            yield result['name']

    def delete_datasource(self, name):
        """Delete a data source by name."""
        rep = requests.delete(
            urljoin(self.url, 'api/datasources/name/%s' % (name,)),
            auth=(self._username, self._password),
        )
        rep.raise_for_status()
        return rep.json()

    def create_influxdb_datasource(self, name, url, database):
        """Create a new InfluxDB data source."""
        rep = requests.post(
            urljoin(self.url, 'api/datasources'),
            auth=(self._username, self._password),
            json={
                'name': name,
                'type': 'influxdb',
                'url': url,
                'database': database,
                'access': 'proxy',
                'basicAuth': False,
            },
        )
        rep.raise_for_status()
        return rep.json()

    def create_dashboard(self, title):
        rep = requests.post(
            urljoin(self.url, 'api/dashboards/db'),
            auth=(self._username, self._password),
            json={
                'dashboard': {
                    'id': None,
                    'schemaVersion': 6,
                    'version': 0,
                    'title': title,
                    'timezone': 'browser',
                    'tags': [],
                },
                'overwrite': False,
            },
        )
        rep.raise_for_status()
        return rep.json()

    def delete_dashboard(self, slug):
        """Delete a dashboard by name."""
        rep = requests.delete(
            urljoin(self.url, 'api/dashboards/db/%s' % (slug,)),
            auth=(self._username, self._password),
        )
        rep.raise_for_status()
        return rep.json()

    def list_dashboards(self):
        rep = requests.get(
            urljoin(self.url, 'api/search'),
            auth=(self._username, self._password),
        )
        rep.raise_for_status()
        for document in rep.json():
            if document['type'] != 'dash-db':
                continue
            slug = document['uri'].split('/', 1)[1]
            yield slug


@pytest.fixture(scope='session')
def grafana_service(docker_ip, docker_services):
    """Wait until Grafana is responsive, return URL."""

    url = 'http://%s:%d' % (
        docker_ip,
        docker_services.port_for('grafana', 3000),
    )
    print('Grafana: URL=', url)
    service = Grafana(url, username='admin', password='admin')

    # Wait until Grafana is responsive.
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1,
        check=service.responsive,
    )
    print('Grafana: responsive!')

    # Ensure the first test starts clean.
    service.cleanup()

    # OK, it's ready to use now.
    return service


@pytest.fixture(scope='function')
def grafana(grafana_service):
    """Ensure Grafana configuration is clean, return URL."""

    # Let the test run.
    yield grafana_service

    # Erase anything leftover by the test.
    grafana_service.cleanup()


@contextmanager
def run_http_service_in_background(routes):
    """Spawn an HTTP service for the duration of a code block.

    ``routes`` is a simple nested ``dict`` like this:

    ::

        def index():
            return {}  # something that is JSON-encodable.

        routes = {
            'GET': {
                '/': index,
            },
        }

    """

    class HTTPRequestHandler(BaseHTTPRequestHandler):
        """Web server that mocks Grafana."""

        def _do(self):
            if self.command not in routes:
                self.send_error(501, "Unsupported method (%r)" % self.command)
                return
            route = routes[self.command].get(self.path, None)
            if route is None:
                self.send_error(404)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', 0)
                self.end_headers()
                return
            try:
                body = route()
            except Exception as error:
                body = str(error)
                body = body.encode('utf-8')
                self.send_error(500)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
                return
            else:
                body = json.dumps(body, indent=2,
                                  sort_keys=True,
                                  separators=(',', ': '))
                body = body.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
                return

        do_GET = _do

    # Start the server in a background thread.
    server = HTTPServer(('0.0.0.0', 0), HTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    # Let the test run.
    yield 'http://127.0.0.1:%d' % (server.server_port,)

    # Stop the server and wait until the background thread finishes.
    print('MockServer: stopping...')
    server.shutdown()
    thread.join()
    print('MockServer: stopped!')


@pytest.fixture(scope='function')
def make_http_service():
    """Return a context manager that mocks an HTTP service."""

    return run_http_service_in_background
