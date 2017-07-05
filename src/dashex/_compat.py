# -*- coding: utf-8 -*-


__all__ = [
    'urljoin',
]


try:  # pragma: no cover
    # py3
    from urllib.parse import urljoin
except ImportError:  # pragma: no cover
    # py2
    from urlparse import urljoin
