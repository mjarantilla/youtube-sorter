#!/usr/bin/env python3

from bin import organizer
from handlers.ranks import RanksHandler
ranks = RanksHandler()

def main(test=False):
    organizer.import_queue(category="primary", test=test)
    organizer.import_queue(category="f1", test=test, date_sorting=True)

def import_queue(category='primary', test=False, max_length: int=None, filler_length: int=None, date_sorting: bool=False):
    playlists = [
        {
            "name": "primary",
            "id": ranks.data['playlist_ids'][category]
        },
        {
            "name": "queue",
            "id": ranks.data['queues'][category]
        },
        {
            "name": "backlog",
            "id": ranks.data['backlogs'][category]
        }
    ]
    playlist_map = {}
    for playlist in playlists:
        playlist_map[playlist['name']] = playlist['id']

    fetched_playlists = organizer.fetch_playlists(playlist_map)

    for fetched_playlist_name in fetched_playlists:
        fetched_playlist = fetched_playlists[fetched_playlist_name]
        if fetched_playlist_name == 'queue':
            organizer.remove_shorts(fetched_playlist, test=test)

main()
