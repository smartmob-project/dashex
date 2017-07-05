# -*- coding: utf-8 -*-


import errno
import os


def ensure_dir(path):
    """Create a folder if it doesn't already exist."""
    print('Creating "%s".' % (path,))
    try:
        os.mkdir(path)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise
    return path
