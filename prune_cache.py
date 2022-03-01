from handlers.cache import VideoCache
from handlers.ranks import RanksHandler
from handlers.playlist import YoutubePlaylist
from handlers.utilities import print_json, ConfigHandler, Logger
import datetime

config = ConfigHandler()
ranks = RanksHandler()
ranks.define_ranks()
playlist_ids = ranks.data['playlist_ids']

cache = VideoCache()
logger = Logger()


def main(quick_prune=False):
    playlists = {}
    vid_ids_in_playlists = []

    logger.write("Fetching playlists")
    for list_of_lists in [ranks.data['backlogs'], ranks.data['playlist_ids'], ranks.data['queues']]:
        for name in list_of_lists:
            playlist_id = list_of_lists[name]
            if playlist_id not in playlists:
                playlists[playlist_id] = YoutubePlaylist(id=playlist_id, cache=cache)

    if not quick_prune:
        logger.write("Collecting existing video IDs from current playlists")
        for pl_id in playlists:
            playlist = playlists[pl_id]
            playlist.get_playlist_items()
            for pl_item in playlist.videos:
                vid_id = pl_item['contentDetails']['videoId']
                vid_ids_in_playlists.append(vid_id)

    search_interval = config.variables['SEARCH_INTERVAL']
    current_datetime = datetime.datetime.now()
    counter = 0
    vid_ids_to_prune = []
    logger.write("Beginning prune")
    for vid_id in cache.data:
        vid_data = cache.data[vid_id]
        counter += 1

        if vid_id not in vid_ids_in_playlists and not quick_prune:
            input("WRONG")
            vid_ids_to_prune.append(vid_id)
        else:
            for field in ['kind', 'etag', 'id']:
                if field in vid_data:
                    vid_data.pop(field)
            if 'contentDetails' in vid_data:
                fields = list(vid_data['contentDetails'].keys())
                for field in fields:
                    if field != 'duration':
                        vid_data['contentDetails'].pop(field)
            if 'snippet' in vid_data:
                for snippet_field in ['defaultAudioLanguage', 'defaultLanguage', 'liveBroadcastContent', 'localized', 'tags']:
                    if snippet_field in vid_data['snippet']:
                        vid_data['snippet'].pop(snippet_field)

    logger.write("Removing videos that don't exist in playlists")
    for vid_id in vid_ids_to_prune:
        cache.data.pop(vid_id)

    new_counter = len(cache.data.keys())

    logger.write("Starting length: %s" % counter)
    logger.write("Ending length: %s" % new_counter)
    logger.write("Videos removed: %s" % len(vid_ids_to_prune))

    cache.write_cache()


main(quick_prune=True)