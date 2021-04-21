"""simpcli3."""

import pkg_resources

version = pkg_resources.get_distribution(__package__).version

from .cli import CliApp, cli_field, get_argparser, ArgumentParser