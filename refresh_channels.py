#!/usr/local/bin/python3.6
from handlers.ranks import RanksHandler
from handlers.subscriptions import SubscriptionsHandler
from handlers.utilities import ConfigHandler
from handlers.utilities import print_json
import argparse, json


def main():
    flags = {
        "verbose": {
            "shorthand": "v",
            "help": ""
        }
    }

    arguments = {
    }

    parser = argparse.ArgumentParser(description='')

    for arg in sorted(arguments):
        dest_var = arg
        shorthand = arguments[arg]['shorthand']
        help_text = arguments[arg]['help']
        parser.add_argument('-' + shorthand, '--' + dest_var, dest=dest_var, help=help_text)

    for flag in sorted(flags):
        dest_var = flag
        shorthand = flags[flag]['shorthand']
        help_text = flags[flag]['help']
        parser.add_argument('-' + shorthand, '--' + dest_var, dest=dest_var, action='store_true', help=help_text)

    args = vars(parser.parse_args())
    fetch(args)


def fetch(args):
    ranks = RanksHandler()
    ranks.define_ranks()
    subs = SubscriptionsHandler()

    subs.update_subscriptions(filtered_channels=ranks.filtered_channels)
    changes = subs.changes

    ranks.update_channels(changes)
    ranks.get_json()
    subs.write()
    ranks.write()

main()
