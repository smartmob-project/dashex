# -*- coding: utf-8 -*-


import pkg_resources


version = pkg_resources.resource_string('dashex', 'version.txt')
version = version.decode('utf-8').strip()
"""Package version (PEP 440 version identifier)."""
