#!/usr/local/bin/python3.6
from handlers.sorter import YoutubePlaylist
import argparse


flags = {
    "all": {
        "shorthand": "a",
        "help": "Specify this if you need assistance formatting the JSON file for the --json|-j argument."
    },
    "verbose": {
        "shorthand": "v",
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
modify_ranks = []
args['f1'] = True
args['primary'] = True
if args['all']:
    args['secondary'] = True
    args['waiting'] = True
for rank in ['f1', 'primary', 'secondary', 'waiting']:
    if args[rank]:
        modify_ranks.append(rank)

for rank in modify_ranks:
    rank_playlist = YoutubePlaylist(rank)
    channels = rank_playlist.get_ordered_channels()
    videos = rank_playlist.get_items()
    for vid_id in videos:
        item = videos[vid_id]
        print("%s: %s" % (item['vid_data']['snippet']['channelTitle'],
                              item['vid_data']['snippet']['title']))

    print()
    sorted = rank_playlist.sort_playlist(import_queue=True)
    print()
    for vid_id in sorted:
        item = sorted[vid_id]
        print("%s: %s" % (item['vid_data']['snippet']['channelTitle'],
                              item['vid_data']['snippet']['title']))
