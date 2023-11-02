#!/usr/bin/env python3

from bin import organizer
from handlers.ranks import RanksHandler
ranks = RanksHandler()

def main(test=False):
    remove_shorts(category="primary", test=test)
    remove_shorts(category="f1", test=test, date_sorting=True)

def remove_shorts(category='primary', test=False):
    playlist_map = {
        "queue": ranks.data['queues'][category]
    }

    fetched_playlists = organizer.fetch_playlists(playlist_map)

    for fetched_playlist_name in fetched_playlists:
        fetched_playlist = fetched_playlists[fetched_playlist_name]
        if fetched_playlist_name == 'queue':
            organizer.remove_shorts(fetched_playlist, test=test)
main()
