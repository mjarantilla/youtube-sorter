from handlers.utilities import ConfigHandler, Logger, print_json
from handlers.client import YoutubeClientHandler
from handlers.playlist import YoutubePlaylist
import os
import json
import datetime

logger = Logger()


class Cache:
    """
    Parent class for all other caches
    """
    def __init__(self, file):
        """
        Initialization method.

        @param file:    The filename of the file which will serve as storage for the cache.
                        Should NOT be the full filepath, as the filepath to the cache directory will be
                        provided by the config variables.
        """
        logger.write("Initializing cache")
        config = ConfigHandler()
        self.dir = config.variables['CACHE_DIR']
        self.file = os.path.join(self.dir, file)
        self.data = None

    def read_cache(self):
        logger.write("Reading cache file: %s" % self.file)
        fp = open(self.file, mode='r')
        self.data = json.load(fp)
        fp.close()

    def write_cache(self):
        logger.write("Writing cache to file: %s" % self.file)
        fp = open(self.file, mode='w')
        print_json(self.data, fp)
        fp.close()

    def add_item(self, **kwargs):
        return None

    def delete_item(self, **kwargs):
        return None

    def check_cache(self, **kwargs):
        return None

    def print_cache(self):
        return None


class ListCache(Cache):
    """
    Class for caches that store lists.
    """
    def __init__(self, file):
        super().__init__(file)
        self.data = []
        self.read_cache()

    def add_item(self, item):
        """
        Adds an element to the end of the cache with the value specified by the 'item' parameter

        @param item: The value to add to the cache.
        @return:
        """
        self.data.append(item)

    def delete_item(self, value):
        """
        Removes the element with the exact value specified by the 'value' parameter

        @param value:   The value to remove from the cache.
        @return:        'value' if the value was successfully removed. If not, returns None
        """
        try:
            self.data.remove(value)
            return value
        except:
            return None

    def print_cache(self):
        for item in self.data:
            print(item)


class MapCache(Cache):
    """
    Class for caches that store dictionaries/maps
    """
    def __init__(self, file):
        super().__init__(file)
        self.data = {}
        self.read_cache()

    def add_item(self, key, data):
        self.data[key] = data

    def delete_item(self, key):
        """

        @param key: The key of the value to remove from the dictionary
        """
        self.data.pop(key)

    def print_cache(self):
        for key in self.data:
            print("%s: %s" % (key, self.data[key]))


class VideoCache(MapCache):
    def __init__(self):
        super().__init__("videos.json")

    def add_playlist_membership(self, vid_id, playlist_id, playlist_item_id, position):
        if self.check_cache(vid_id):
            self.data[vid_id]['playlist_membership'][playlist_id] = {
                'playlist_item_id': playlist_item_id,
                'position': position
            }
            self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()
            self.write_cache()

    def remove_playlist_membership(self, vid_id, playlist_id):
        if self.check_cache(vid_id):
            if playlist_id in self.data[vid_id]['playlist_membership']:
                self.data[vid_id]['playlist_membership'].pop(playlist_id)
            self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()
            self.write_cache()

    def add_video(self, vid_id):
        client_handler = YoutubeClientHandler()
        request = client_handler.client.videos().list(
            part='snippet,contentDetails',
            id=vid_id
        )
        response = client_handler.execute(request)
        vid_data = response['items'][0] if len(response['items']) > 0 else None
        logger.write("Video data queried. Adding to cache.... ")
        self.add_item(vid_id, vid_data)
        if 'playlist_membership' not in self.data[vid_id]:
            self.data[vid_id]['playlist_membership'] = {}
        if 'current_playlist' not in self.data[vid_id]:
            self.data[vid_id]['current_playlist'] = None
        if 'date_cached' not in self.data[vid_id]:
            self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()
        self.write_cache()

        return vid_data

    def check_cache(self, vid_id, update=False):
        """
        Checks the cache for a video.

        @param vid_id:  The YouTube video ID
        @param update:  If the video data is not found in the cache, query YouTube and add it
        @return:        None if add==False and vid_id is not in the cache, OR video metadata if vid_id is in cache
        """
        msg = "Checking cache.... "
        if vid_id not in self.data:
            msg += "Not found. "
            if update:
                vid_data = self.add_video(vid_id)

                return vid_data
            else:
                logger.write(msg)
                return None
        else:
            msg += "FOUND"
            vid_data = self.data[vid_id]
            logger.write(msg)
            return vid_data

    def sync_local_with_yt(self, playlist_id):
        """
        This method will ensure that the local cache data reflects the current state of the specified playlist

        @param playlist_id: The playlist to sync to the local cache
        @return:
        """

        playlist = YoutubePlaylist(id=playlist_id, cache=self)
        logger.write("Synchronizing local cache with Playlist \"%s\"" % playlist_id)
        playlist.get_playlist_items()

        playlist_videos = {}
        for playlist_item in playlist.videos:
            vid_id = playlist_item['contentDetails']['videoId']
            playlist_videos[vid_id] = playlist_item

        for vid_id in self.data:
            vid_data = self.data[vid_id]
            playlist_membership = vid_data['playlist_membership']
            if vid_id in playlist_videos:
                playlist_item_id = playlist_videos[vid_id]['id']
                position = playlist_videos[vid_id]['snippet']['position']
                self.add_playlist_membership(vid_id, playlist_id, playlist_item_id, position)
            elif vid_id not in playlist_videos and playlist_id in playlist_membership:
                self.remove_playlist_membership(vid_id, playlist_id)
            playlist_videos.pop(vid_id)

        logger.write("%i videos found in playlist that are not in cache" % len(playlist_videos))
        for vid_id in playlist_videos:
            playlist_item = playlist_videos[vid_id]
            playlist_item_id = playlist_item['id']
            position = playlist_item['snippet']['position']
            title = playlist_item['snippet']['title']
            logger.write("Adding to cache: %s" % title)
            self.add_video(vid_id)
            self.add_playlist_membership(vid_id, playlist_id, playlist_item_id, position)
            logger.write()


class PlaylistCache(ListCache):
    def __init__(self, file, playlist_id):
        super().__init__(file)
        self.id = playlist_id
