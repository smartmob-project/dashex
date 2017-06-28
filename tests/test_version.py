# -*- coding: utf-8 -*-


from __future__ import print_function

import mock
import pytest
import subprocess

from dashex import version
from dashex.__main__ import main


def test_run_as_function(capsys):
    """``dashex --verion`` prints the version number."""
    with pytest.raises(SystemExit) as exc:
        print(main(['--version']))
    assert exc.value.code == 0
    output, errors = capsys.readouterr()
    if output:
        # py3
        assert errors == ''
        assert output.strip() == version
    else:
        # py2
        assert output == ''
        assert errors.strip() == version


def test_run_as_entrypoint(capsys):
    """``dashex --verion`` prints the version number."""
    with mock.patch('sys.argv', ['...', '--version']):
        with pytest.raises(SystemExit) as exc:
            print(main())
    assert exc.value.code == 0
    output, errors = capsys.readouterr()
    if output:
        # py3
        assert errors == ''
        assert output.strip() == version
    else:
        # py2
        assert output == ''
        assert errors.strip() == version


def test_run_as_command(capsys):
    """``dashex --verion`` prints the version number."""
    output = subprocess.check_output(
        ['dashex', '--version'],
        stderr=subprocess.STDOUT,
    )
    assert output.decode('utf-8').strip() == version
