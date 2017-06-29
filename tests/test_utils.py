# -*- coding: utf-8 -*-


import errno
import mock
import os.path
import pytest

from dashex._utils import (
    ensure_dir,
)


def test_ensure_dir(tmpdir):
    """Re-creating an existing folder is a no-op."""

    path = os.path.join(str(tmpdir), 'foo')

    assert not os.path.isdir(path)

    # If it doesn't already exist, it is created.
    ensure_dir(path)
    assert os.path.isdir(path)

    # If it already exists, the request is ignored.
    ensure_dir(path)
    assert os.path.isdir(path)


def test_ensure_dir_unexpected_error():
    """Re-creating an existing folder is a no-op."""

    class MockOSError(OSError):
        @property
        def errno(self):
            return errno.EPERM

    e = MockOSError()
    with mock.patch('os.mkdir') as mkdir:
        mkdir.side_effect = [e]
        with pytest.raises(OSError) as exc:
            ensure_dir('foo')
        assert exc.value is e
