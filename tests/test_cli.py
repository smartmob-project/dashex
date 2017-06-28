# -*- coding: utf-8 -*-


from __future__ import print_function

import pytest

from dashex import version
from dashex.__main__ import main


def test_version(capsys):
    """``dashex --verion`` prints the version number."""
    with pytest.raises(SystemExit) as exc:
        print(main(['--version']))
    assert exc.value.code == 0
    output, errors = capsys.readouterr()
    if output:
        assert errors == ''
        assert output.strip() == version
    else:
        assert output == ''
        assert errors.strip() == version
