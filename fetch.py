#!/usr/local/bin/python3.6
from handlers.queue import QueueHandler, LegacyRecords
from handlers.utilities import Logger
import argparse


def merge(legacy_filepath):
    records = LegacyRecords(legacy_filepath=legacy_filepath)
    records.combine_data()
    records.write_records()

flags = {
    "all": {
        "shorthand": "a",
        "help": "Specify this if you need assistance formatting the JSON file for the --json|-j argument."
    },
    "verbose": {
        "shorthand": "v",
        "help": ""
    },
    "f1": {
        "shorthand": "f",
        "help": ""
    },
    "primary": {
        "shorthand": "p",
        "help": ""
    },
    "secondary": {
        "shorthand": "s",
        "help": ""
    },
    "waiting": {
        "shorthand": "w",
        "help": ""
    }
}

arguments = {
    "merge": {
        "shorthand": "m",
        "help": "Merge legacy records"
    }
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
if args['merge'] is not None:
    print("Merging")
    merge(legacy_filepath=args['merge'])
ranks = []
args['f1'] = True
args['primary'] = True
if args['all']:
    args['secondary'] = True
    args['waiting'] = True
for rank in ['f1', 'primary', 'secondary', 'waiting']:
    if args[rank]:
        ranks.append(rank)
queue = QueueHandler()
if args['all']:
    queue.scan_channels(all_videos=True)
else:
    queue.scan_ordered_channels(ranks)