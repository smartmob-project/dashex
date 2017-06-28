# -*- coding: utf-8 -*-


from __future__ import print_function

import pytest
import requests
import requests.exceptions

try:
    # py3
    from urllib.parse import urljoin
except ImportError:
    # py2
    from urlparse import urljoin


class InfluxDB(object):
    """Low-level InfluxDB client (automate HTTP requests)."""

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        return self._url

    def responsive(self):
        """Check if InfluxDB is responsive."""
        print('Pinging InfluxDB...')
        rep = requests.get(urljoin(self.url, 'ping'))
        rep.raise_for_status()
        return True

    def cleanup(self):
        """Ensure InfluxDB is empty to prevent test cross-contamination."""
        print('Cleaning up InfluxDB.')
        for name in self.show_databases():
            print('Deleting database "%s".' % (name,))
            self.drop_database(name)

    def query(self, text):
        """Execute a query."""
        rep = requests.get(urljoin(self.url, 'query'), params={'q': text})
        rep.raise_for_status()
        return rep.json()['results']

    def create_database(self, name):
        """Create a database."""
        print('Creating database "%s".' % (name,))
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
    print('Influx DB URL:', url)
    service = InfluxDB(url)

    # Wait until InfluxDB is responsive.
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1,
        check=service.responsive,
    )
    print('InfluxDB is responsive!')

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

    def responsive(self):
        """Check if Grafana is responsive."""
        print('Pinging Grafana...')
        try:
            rep = requests.get(self.url)
        except requests.exceptions.ConnectionError:
            return False
        rep.raise_for_status()
        return True

    def cleanup(self):
        """Ensure Grafana is empty to prevent test cross-contamination."""
        print('Cleaning up Grafana.')
        for name in self.list_datasources():
            print('Deleting datasource "%s".' % (name,))
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
                'database': database,
                'url': url,
                'access': 'proxy',
                'basicAuth': False,
            },
        )
        rep.raise_for_status()
        return rep.json()


@pytest.fixture(scope='session')
def grafana_service(docker_ip, docker_services):
    """Wait until Grafana is responsive, return URL."""

    url = 'http://%s:%d' % (
        docker_ip,
        docker_services.port_for('grafana', 3000),
    )
    print('Grafana URL:', url)
    service = Grafana(url, username='admin', password='admin')

    # Wait until Grafana is responsive.
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1,
        check=service.responsive,
    )
    print('Grafana is responsive!')
    
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
