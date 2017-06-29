# -*- coding: utf-8 -*-


import json
import glob
import os.path
import pkg_resources
import requests
import requests.exceptions
import time
import timeit

from ._compat import urljoin
from ._utils import ensure_dir


version = pkg_resources.resource_string('dashex', 'version.txt')
version = version.decode('utf-8').strip()
"""Package version (PEP 440 version identifier)."""


def get_json(host, path, credentials=None):
    """Download a JSON object."""

    rep = requests.get(
        urljoin(host, path),
        auth=credentials,
    )
    rep.raise_for_status()
    return rep.json()


def post_json(host, path, data={}, credentials=None):
    """Upload a JSON object."""

    rep = requests.post(
        urljoin(host, path),
        auth=credentials,
        headers={
            'Content-Type': 'application/json',
        },
        data=json.dumps(data),
    )
    rep.raise_for_status()
    return rep.json()


def put_json(host, path, data={}, credentials=None):
    """Upload a JSON object."""

    rep = requests.put(
        urljoin(host, path),
        auth=credentials,
        headers={
            'Content-Type': 'application/json',
        },
        data=json.dumps(data),
    )
    rep.raise_for_status()
    return rep.json()


def json_pp(doc):
    """Render JSON in normalized format."""
    return json.dumps(doc, indent=2, sort_keys=True, separators=(',', ': '))


def grafana_wait(grafana_url, username, password,
                 timeout=None, clock=timeit.default_timer):
    """Poll Grafana until its API is repsonsive."""

    ref = clock()

    def elapsed():
        return clock() - ref

    while (timeout is None) or (elapsed() < timeout):
        print('Pinging Grafana...')
        try:
            rep = requests.get(
                urljoin(grafana_url, 'api/admin/stats'),
                auth=(username, password),
            )
        except requests.exceptions.ConnectionError:
            print('  not ready, retrying in 1 second...')
            time.sleep(1.0)
            continue
        rep.raise_for_status()
        print('  ready!')
        return

    raise Exception('Grafana is unresponsive at this time.')


def grafana_pull(grafana_url, username, password, output_path):
    """Pull Grafana configuration to disk."""

    # Prepare to store contents on disk.
    ensure_dir(output_path)
    output_path = os.path.join(output_path, 'grafana')
    ensure_dir(output_path)

    # Fetch all data sources.
    ensure_dir(os.path.join(output_path, 'datasources'))
    for document in get_json(grafana_url, 'api/datasources',
                             credentials=(username, password)):
        slug = document['name']
        path = os.path.join(output_path, 'datasources', '%s.json' % (slug,))
        print(path)
        for field in ('id', 'orgId', 'typeLogoUrl'):
            del document[field]
        with open(path, 'wb') as stream:
            stream.write(json_pp(document).encode('utf-8'))
            stream.write(b'\n')

    # Fetch all dashboards (except Home, which we can't edit).
    ensure_dir(os.path.join(output_path, 'dashboards'))
    for document in get_json(grafana_url, 'api/search',
                             credentials=(username, password)):
        if document['type'] != 'dash-db':
            continue
        slug = document['uri'].split('/', 1)[1]
        document = get_json(grafana_url, 'api/dashboards/db/%s' % (slug,),
                            credentials=(username, password))
        del document['dashboard']['id']
        path = os.path.join(output_path, 'dashboards', '%s.json' % (slug,))
        print(path)
        with open(path, 'wb') as stream:
            stream.write(json_pp(document).encode('utf-8'))
            stream.write(b'\n')


def grafana_push(grafana_url, username, password, input_path):
    """Push on-disk configuration to Grafana."""

    # Ensure Grafana is responsive (a common need for this tool is to provision
    # the infrastructure right after creating the resources and some
    # provisionning tools don't wait for the infra to be responsive before
    # returning, so we compensate here).
    grafana_wait(grafana_url, username, password)

    # Create/update data sources.
    datasources = {
        document['name']: document['id']
        for document in get_json(grafana_url, 'api/datasources',
                                 credentials=(username, password))
    }
    for path in glob.iglob(os.path.join(input_path, 'grafana',
                                        'datasources', '*.json')):
        print(path)
        with open(path, 'rb') as stream:
            document = json.loads(stream.read().decode('utf-8'))

        # Create or update depending on whether it already exists.
        if document['name'] in datasources:
            # TODO: check if we should allow forced upload.
            document['id'] = datasources.get(document['name'], None)
            document['overwrite'] = False
            print('Updating data source "%s" with ID #%s.' % (
                document['name'],
                document['id'],
            ))
            put_json(grafana_url, 'api/datasources/%s' % (document['id'],),
                     data=document, credentials=(username, password))
        else:
            print(json.dumps(document, indent=2, sort_keys=True))
            rep = post_json(grafana_url, 'api/datasources',
                            data=document, credentials=(username, password))
            print('Created data source "%s" with ID #%d.' % (
                document['name'],
                rep['id'],
            ))
        print()

    print('---')

    # Create/update dashboards.
    dashboards = {
        document['uri'].split('/', 1)[1]: document['id']
        for document in get_json(grafana_url, 'api/search',
                                 credentials=(username, password))
    }
    print('DASHBOARDS:', dashboards)
    for path in glob.iglob(os.path.join(input_path, 'grafana',
                                        'dashboards', '*.json')):
        print(path)
        with open(path, 'rb') as stream:
            document = json.loads(stream.read().decode('utf-8'))
        slug = document['meta']['slug']
        del document['meta']
        document['dashboard']['id'] = dashboards.get(slug, None)
        print('ID:', document['dashboard']['id'])
        if document['dashboard']['id'] is None:
            print('Creating dashboard "%s" with slug "%s".' % (
                document['dashboard']['title'],
                slug,
            ))
        else:
            print('Updating dashboard "%s" with slug "%s" and ID #%d.' % (
                document['dashboard']['title'],
                slug,
                document['dashboard']['id'],
            ))
        try:
            post_json(grafana_url, 'api/dashboards/db',
                      data=document, credentials=(username, password))
        except requests.exceptions.HTTPError as error:
            # We'll get a version-mismatch error if Grafana already has the
            # latest version (or a newer version).
            if error.response.status_code != 412:
                raise
            print(error.response.json()['message'])
        print()
