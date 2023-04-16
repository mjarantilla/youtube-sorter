#!/usr/bin/env python3
from handlers import playlist
from handlers.ranks import RanksHandler
from handlers.cache import VideoCache
from handlers.playlist import YoutubePlaylist
from handlers.client import YoutubeClientHandler
from handlers.utilities import Logger, ConfigHandler, print_json
import argparse as ap
import sys

logger = Logger()
logger.write("--------------------------------------------")
logger.write("LISTING VIDEOS")
logger.write("--------------------------------------------", delim=True)
logger.write("Initializing caches and configs")
ranks = RanksHandler()
cache = VideoCache()
config = ConfigHandler()
client = YoutubeClientHandler('token.pickle')
logger.write("Initialization of objects complete", delim=True, header=True)


def parse_args():
    """ Get user provided command line arguments """

    parser = ap.ArgumentParser()

    # Dictionary of arguments. Each argument is represented by its own dictionary.
    # Except for 'shorthand', each key corresponds to a kwarg for ap.ArgumentParser().add_argument()
    # More kwargs can be added as needed, e.g. nargs
    arguments = {
        # 'session-report-file': {
        #     'shorthand': 'f',
        #     'help': "The full path of the session report to process for SCLK interpolation"
        # }
    }

    # Dictionary of true/false flags. Similar to the dictionary of arguments, except these are only true/false flags.
    flags = {
        'primary': {
            'shorthand': 'p',
            'help': 'List primary'
        },
        'f1': {
            'shorthand': 'f',
            'help': 'List F1'
        },
        'secondary': {
            'shorthand': 's',
            'help': 'List secondary'
        },
        'backlog': {
            'shorthand': 'b',
            'help': 'List backlog'
        },
        'queue': {
            'shorthand': 'q',
            'help': 'List queue'
        }
    }

    # Add arguments to parser object
    for arg in sorted(arguments):
        argument = arguments[arg]
        shorthand = argument['shorthand']
        parser_kwargs = {
            'dest': arg
        }

        for kwarg in argument:
            # Ignores the 'shorthand' kwarg when adding args to the parser
            # because 'shorthand' is only used internally to this script
            if kwarg not in ['shorthand']:
                parser_kwargs[kwarg] = argument[kwarg]
        if arguments[arg]['shorthand']:
            parser.add_argument('-' + shorthand, '--' + arg, **parser_kwargs)
        else:
            parser.add_argument('--' + arg, **parser_kwargs)

    # Add flags to parser object
    for flag in sorted(flags):
        shorthand = flags[flag]['shorthand']
        parser_kwargs = {
            'dest': flag,
            'action': 'store_true'
        }
        for kwarg in flags[flag]:
            # Ignores the 'shorthand' kwarg when adding args to the parser
            # because 'shorthand' is only used internally to this script
            if kwarg not in ['shorthand']:
                parser_kwargs[kwarg] = flags[flag][kwarg]

        if shorthand is None:
            parser.add_argument('--' + flag, **parser_kwargs)
        else:
            parser.add_argument('-' + shorthand, '--' + flag, **parser_kwargs)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Get the command line arguments and apply defaults if no input was made and a default is available
    args = vars(parser.parse_args())
    for arg in args:
        if arg in arguments:
            if args[arg] is None and 'default' in arguments[arg]:
                args[arg] = arguments[arg]['default']

    return args


def create_playlist_map(playlists):
    playlist_map = {}
    for playlist in playlists:
        playlist_map[playlist] = ranks.data['playlist_ids'][playlist]

    return playlist_map


def print_playlist_videos(playlist_name, playlist_id):
    playlist = YoutubePlaylist(playlist_id, cache=cache)
    playlist.get_playlist_items()
    channel_dict = {}
    channel_order = []
    videos = []
    channels = []
    total_vids = 0
    for video in playlist.videos:
        channel = video['snippet']['videoOwnerChannelTitle']
        title = video['snippet']['title']
        position = video['snippet']['position']
        if channel not in channel_dict:
            channel_dict[channel] = []
            channel_order.append(channel)
        channel_dict[channel].append(title)
        videos.append((channel, title))
        total_vids += 1

    for channel in channel_order:
        channel_data = {
            'channel': channel,
            'videos': channel_dict[channel]
        }
        channels.append(channel_data)

    output = {
        'count': total_vids,
        'channels': channels,
        'videos': videos
    }
    print("  Count: {}".format(total_vids))
    print()
    print("  Channels:")
    for channel_data in channels:
        channel_title = channel_data['channel']
        channel_videos = channel_data['videos']
        print("    {}".format(channel_title))
        for video_title in channel_videos:
            print("      {}".format(video_title))
    print()
    print("  CSV")
    for video in videos:
        print("\"{}\"\t\"{}\"\t\"{}\"".format(playlist_name, video[0], video[1]))
    print()


def main():
    args = parse_args()
    playlists = []
    for arg in args:
        if args[arg]:
            playlists.append(arg)

    playlist_map = create_playlist_map(playlists)
    for playlist in playlist_map:
        print("======================================================")
        print("Playlist: {}".format(playlist))
        print_playlist_videos(playlist, playlist_map[playlist])


main()
