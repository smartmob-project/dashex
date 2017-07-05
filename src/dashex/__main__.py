# -*- coding: utf-8 -*-


import argparse
import sys

from . import (
    version,
    grafana_pull,
    grafana_push,
)


cli = argparse.ArgumentParser('dashex')
cli.add_argument('--version', action='version', version=version)

commands = cli.add_subparsers(title='commands')

command = commands.add_parser('grafana-pull')
command.set_defaults(func=grafana_pull)
command.add_argument('-i, --instance', type=str,
                     action='store', dest='grafana_url')
command.add_argument('-u, --username', type=str,
                     action='store', dest='username', default=None)
command.add_argument('-p, --password', type=str,
                     action='store', dest='password', default=None)
command.add_argument('-o, --output', type=str,
                     action='store', dest='output_path', default='.')

command = commands.add_parser('grafana-push')
command.set_defaults(func=grafana_push)
command.add_argument('-i, --instance', type=str,
                     action='store', dest='grafana_url')
command.add_argument('-u, --username', type=str,
                     action='store', dest='username', default=None)
command.add_argument('-p, --password', type=str,
                     action='store', dest='password', default=None)
command.add_argument('-o, --output', type=str,
                     action='store', dest='input_path', default='.')


def main(arguments=None):
    """Command-line entry point."""

    if arguments is None:
        arguments = sys.argv[1:]
    arguments = cli.parse_args(arguments)

    # Recover arguments in dict form.
    args = dict(arguments._get_kwargs())

    # Recover the function attached to the sub-command.
    func = args.pop('func', None)

    func(**args)

    print('DONE!')


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
