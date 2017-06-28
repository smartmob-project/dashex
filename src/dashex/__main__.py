# -*- coding: utf-8 -*-


import argparse
import sys

from . import version


cli = argparse.ArgumentParser('runwith')
cli.add_argument('--version', action='version', version=version)


def main(arguments=None):
    """Command-line entry point."""

    if arguments is None:
        arguments = sys.argv[1:]
    arguments = cli.parse_args(arguments)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
