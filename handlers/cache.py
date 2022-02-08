from handlers.utilities import ConfigHandler, Logger, print_json
from handlers.client import YoutubeClientHandler
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
        config = ConfigHandler()
        self.dir = config.variables['CACHE_DIR']
        self.file = os.path.join(self.dir, file)
        self.data = None

    def read_cache(self):
        fp = open(self.file, mode='r')
        self.data = json.load(fp)
        fp.close()

    def write_cache(self):
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

    def check_cache(self, vid_id, update=False):
        """
        Checks the cache for a video.
        @param vid_id:  The YouTube video ID
        @param update:  If the video data is not found in the cache, query YouTube and add it
        @return:        None if add==False and vid_id is not in the cache, OR video metadata if vid_id is in cache
        """
        if vid_id not in self.data:
            if update:
                client = YoutubeClientHandler().client
                request = client.videos().list(
                    part='snippet,contentDetails',
                    id=vid_id
                )
                response = request.execute()
                vid_data = response['items'][0] if len(response['items']) > 0 else None
                self.data[vid_id] = vid_data
                if 'playlist_membership' not in self.data[vid_id]:
                    self.data[vid_id]['playlist_membership'] = {}
                if 'current_playlist' not in self.data[vid_id]:
                    self.data[vid_id]['current_playlist'] = None
                if 'date_cached' not in self.data[vid_id]:
                    self.data[vid_id]['date_cached'] = datetime.datetime.now().timestamp()

                return vid_data
            else:
                return None
        else:
            vid_data = self.data[vid_id]

            return vid_data


class PlaylistCache(ListCache):
    def __init__(self, file, playlist_id):
        super().__init__(file)
        self.id = playlist_id
