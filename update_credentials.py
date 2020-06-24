#!/usr/local/bin/python3.6

from handlers.client import YoutubeClientHandler
from handlers.utilities import ConfigHandler
import argparse

handler = ConfigHandler()

flags = {
    "clear": {
        "shorthand": "c",
        "help": "Clear token"
    }
}

arguments = {
    "token": {
        "shorthand": "t",
        "help": "Token filepath",
        "default": "token.pickle"
    },
    "credentials_filepath": {
        "shorthand": "f",
        "help": "Credentials filepath",
        "default": handler.secrets_filepath
    }
}

parser = argparse.ArgumentParser(description='')

for arg in sorted(arguments):
    dest_var = arg
    shorthand = arguments[arg]['shorthand']
    help_text = arguments[arg]['help']
    parser.add_argument('-' + shorthand, '--' + dest_var, dest=dest_var, help=help_text)

args = vars(parser.parse_args())

for arg in args:
    if args[arg] is None:
        if 'default' in arguments[arg]:
            args[arg] = arguments[arg]['default']

youtube = YoutubeClientHandler(
    pickle=args['token'],
    secrets_filepath=args['credentials_filepath'],
    clear=args['clear']
)