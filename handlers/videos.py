from handlers.utilities import ConfigHandler, Logger, print_json
from handlers.client import YoutubeClientHandler
from handlers.cache import VideoCache

logger = Logger()


class Video:
    def __init__(self, id):
        """

        @param id:  The YouTube-assigned unique ID for the video
        """
        self.config = ConfigHandler()
        self.cache = VideoCache()
        self.id = id
        self.data = None
        self.title = None
        self.snippet = None
        self.contentDetails = None
        self.playlist_membership = {}
        self.current_playlist = None
        self.get_video_data()

    def get_video_data(self, update=True):
        """
        @param update: Boolean which tells the method to query the YouTube API for the video data is the video data
                    doesn't exist in the cache file
        @return:    None
        """
        self.data = self.cache.check_cache(self.id, update)
        self.snippet = self.data['snippet']
        self.contentDetails = self.data['contentDetails']
        self.title = self.snippet['title']
        self.playlist_membership = self.data['playlist_membership']
        self.current_playlist = self.data['current_playlist']

    def update_cache(self, update=True):
        self.cache.check_cache(self.id, update)
        self.cache.data[self.id]['playlist_membership'] = self.playlist_membership
        self.cache.data[self.id]['current_playlist'] = self.current_playlist

    def add_to_playlist(self, playlist_id, position=0):
        """

        @param playlist_id: The playlist ID of the destination playlist
        @param position:    The position at which to add the video to
        @return:            The REST response
        """
        client_handler = YoutubeClientHandler()
        response = None
        properties = {
            'snippet.playlistId': playlist_id,
            'snippet.resourceId.kind': 'youtube#video',
            'snippet.resourceId.videoId': self.id,
            'snippet.position': position,
        }

        if playlist_id not in self.playlist_membership:
            playlist_item = client_handler.playlist_items_insert(properties, part='snippet')
            self.playlist_membership[playlist_id] = {
                'playlist_item_id': playlist_item['id'],
                'position': position
            }
            self.current_playlist = playlist_id
        else:
            if position != self.playlist_membership[playlist_id]['position']:
                playlist_item = client_handler.playlist_item_update_position(properties, part='snippet')
                self.playlist_membership[playlist_id] = {
                    'playlist_item_id': playlist_item['id'],
                    'position': position
                }

        self.update_cache()

        return response

    def remove_from_playlist(self, playlist_id):
        return None