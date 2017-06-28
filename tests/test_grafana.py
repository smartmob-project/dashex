# -*- coding: utf-8 -*-


import requests

from urllib import urlencode


def test_grafana(influxdb, grafana):
    influxdb.create_database('foo')
    print(influxdb.show_databases())
    print(grafana.create_influxdb_datasource('foo', influxdb.url, 'foo'))
