from handlers.utilities import ConfigHandler, Logger, print_json
from handlers.client import YoutubeClientHandler
import os
import json
import datetime

logger = Logger(tier=4)


class Cache:
    """
    Parent class for all other caches
    """
    def __init__(self, file, client=None):
        """
        Initialization method.

        @param file:    The filename of the file which will serve as storage for the cache.
                        Should NOT be the full filepath, as the filepath to the cache directory will be
                        provided by the config variables.
        """
        logger.write("Initializing cache")
        self.config = ConfigHandler()
        self.dir = self.config.variables['CACHE_DIR']
        self.file = os.path.join(self.dir, file)
        self.data = None
        self.client = client if client is not None else YoutubeClientHandler()

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

    def check_playlist_membership(self, vid_id, playlist_id):
        if self.check_cache(vid_id):
            if playlist_id in self.data[vid_id]['playlist_membership']:
                return True

        return False

    def add_playlist_membership(self, vid_id, playlist_id, playlist_item_id, position, update=True):
        if self.check_cache(vid_id, update):
            self.data[vid_id]['playlist_membership'][playlist_id] = {
                'playlist_item_id': playlist_item_id,
                'position': position
            }
            self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()

    def remove_playlist_membership(self, vid_id, playlist_id, update=False):
        logger.write("Removing playlist membership")
        if self.check_cache(vid_id, update):
            if playlist_id in self.data[vid_id]['playlist_membership']:
                self.data[vid_id]['playlist_membership'].pop(playlist_id)
                self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()

    def _is_private(self, vid_id, response_obj):
        # Load data about videos marked "private" on YouTube
        private_videos_file = self.config.variables['PRIVATE_VIDEOS_FILE']
        private_fp = open(private_videos_file, mode='r')
        private_vids_data = json.load(private_fp)
        private_videos = private_vids_data['private_videos']
        private_fp.close()

        private = False

        video = response_obj['items'][0] if 'items' in response_obj and len(response_obj['items']) > 0 else None
        if not video:
            private_videos.append(vid_id)
            private = True

        private_fp = open(private_videos_file, mode='w')
        json.dump({'private_videos': private_videos}, fp=private_fp, separators=(',', ': '), indent=2, sort_keys=True)
        private_fp.close()

        return private

    def add_video(self, vid_id):
        client_handler = self.client
        request = client_handler.client.videos().list(
            part='snippet,contentDetails',
            id=vid_id
        )
        response = client_handler.execute(request)
        if not self._is_private(vid_id, response):
            vid_data = response['items'][0] if len(response['items']) > 0 else None
            logger.write("Adding to cache: %s" % vid_data['snippet']['title'])
            self.add_item(vid_id, vid_data)
            if 'playlist_membership' not in self.data[vid_id]:
                self.data[vid_id]['playlist_membership'] = {}
            if 'date_cached' not in self.data[vid_id]:
                self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()

            return vid_data

        return None

    def check_cache(self, vid_id, update=False):
        """
        Checks the cache for a video.

        @param vid_id:  The YouTube video ID
        @param update:  If the video data is not found in the cache, query YouTube and add it
        @return:        None if add==False and vid_id is not in the cache, OR video metadata if vid_id is in cache
        """

        # If vid_id doesn't exist OR if the vid_id was erroneously entered with null data
        if vid_id not in self.data or vid_id in self.data and self.data[vid_id] is None:
            msg = "%s not found. " % vid_id
            if update:
                vid_data = self.add_video(vid_id)

                return vid_data
            else:
                logger.write(msg)
                return None
        else:
            vid_data = self.data[vid_id]
            channel = vid_data['snippet']['channelTitle']
            title = vid_data['snippet']['title']
            return vid_data


class PlaylistCache(ListCache):
    def __init__(self, file, playlist_id):
        super().__init__(file)
        self.id = playlist_id
        self.data = {
            'video_list': [],
            'video_metadata': []
        }

    def add_item(self, item):
        video = item
        self.data['video_list'].append((video.channel_name, video.title))
        self.data['video_metadata'].append(video.data)

    def print_cache(self):
        print_json(self.data)