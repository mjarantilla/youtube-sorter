#!/usr/bin/env python3

from bin import organizer
from handlers.ranks import RanksHandler
from handlers.cache import VideoCache
from handlers.utilities import ConfigHandler, print_json
from handlers.videos import Video
import json


def main(test=False):
    organizer.import_queue(category="secondary", test=test, max_length=300, date_sorting=True)


def organize_no_sort():
    ranks = RanksHandler()
    cache = VideoCache()
    config = ConfigHandler()
    category = "secondary"
    playlists = [
        {
            "name": "primary",
            "id": ranks.data['playlist_ids'][category]
        },
        {
            "name": "queue",
            "id": ranks.data['queues'][category]
        },
        # {
        #     "name": "backlog",
        #     "id": ranks.data['backlogs'][category]
        # }
    ]
    secondary_playlist_id = ranks.data['playlist_ids'][category]
    queue_playlist_id = ranks.data['queues'][category]

    subs_fp = open(config.variables['SUBSCRIPTIONS_FILE'], mode="r")
    subscriptions = json.load(subs_fp)['details']

    playlist_map = {}
    playlist_map['queue'] = queue_playlist_id

    fetched_playlists = organizer.fetch_playlists(playlist_map)

    for fetched_playlist_name in fetched_playlists:
        fetched_playlist = fetched_playlists[fetched_playlist_name]
        if fetched_playlist_name == 'queue':
            organizer.remove_shorts(fetched_playlist)

    print("fetching queue playlist")
    playlist_videos = {}
    for fetched_playlist_name in fetched_playlists:
        playlist = fetched_playlists[fetched_playlist_name]
        playlist_videos[playlist.id] = []
        for video in playlist.videos:
            playlist_videos[playlist.id].append(Video(video['contentDetails']['videoId'], cache))

    print("Determining tier videos")
    tier_vids = organizer.determine_tier_videos(
        playlist_videos=playlist_videos,
        tier_name="secondary",
        cache=cache,
        subscriptions=subscriptions
    )

    for vid in tier_vids:
        vid.check_playlist_membership(queue_playlist_id)
        queue_playlist_item = vid.data['playlist_membership'][queue_playlist_id]

        vid.add_to_playlist(secondary_playlist_id, 0)
        vid.remove_from_playlist(queue_playlist_id, playlist_item_id=queue_playlist_item['playlist_item_id'])

organize_no_sort()

# main()