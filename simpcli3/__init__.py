"""simpcli3."""

import pkg_resources

version = pkg_resources.get_distribution(__package__).version

from simple_parsing import Serializable
from .cli import CliApp, cli_field, get_argparser, ArgumentParser