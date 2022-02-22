from handlers.utilities import ConfigHandler, Logger, print_json
from handlers.client import YoutubeClientHandler
from handlers.playlist import YoutubePlaylist
import json

logger = Logger()


class Video:
    def __init__(self, id, cache, **kwargs):
        """

        @param id:  The YouTube-assigned unique ID for the video
        """
        self.id = id
        self.config = ConfigHandler() if 'config' not in kwargs else kwargs['config']
        self.cache = cache
        self.private = self._check_if_private()
        self.client = YoutubeClientHandler() if 'client' not in kwargs else kwargs['client']
        self.data = self.cache.check_cache(self.id, update=True)
        self.title = self.data['snippet']['title']

    def _check_if_private(self):
        # Load data about videos marked "private" on YouTube
        private_videos_file = self.config.variables['PRIVATE_VIDEOS_FILE']
        private_fp = open(private_videos_file, mode='r')
        private_vids_data = json.load(private_fp)
        private_videos = private_vids_data['private_videos']
        private_fp.close()

        if self.id in private_videos:
            if self.cache.check_cache(self.id, True):
                return True

        return False

    def add_to_playlist(self, playlist_id, position=0):
        """
        Adds the video to the specified playlist at the specified position.

        @param playlist_id: The playlist ID of the destination playlist
        @param position:    The position at which to add the video to. Defaults to 0 (first position)
        @return:            The REST response
        """
        response = None
        params = {
            'snippet.playlistId': playlist_id,
            'snippet.resourceId.kind': 'youtube#video',
            'snippet.resourceId.videoId': self.id,
            'snippet.position': position,
        }

        if playlist_id not in self.data['playlist_membership']:
            playlist_item = self.client.playlist_items_insert(params, part='snippet')
            self.data['playlist_membership'][playlist_id] = {
                'playlist_item_id': playlist_item['id'],
                'position': position
            }
            self.data['current_playlist'] = playlist_id
            self.cache.add_playlist_membership(self.id, playlist_id, playlist_item['id'], position)
            logger.write("Added to playlist:")
        else:
            if position != self.data['playlist_membership'][playlist_id]['position']:
                playlist_item_id = self.data['playlist_membership'][playlist_id]['playlist_item_id']
                params['id'] = playlist_item_id
                playlist_item = self.client.playlist_item_update_position(params, part='snippet')
                self.data['playlist_membership'][playlist_id] = {
                    'playlist_item_id': playlist_item['id'],
                    'position': position
                }
                self.cache.add_playlist_membership(self.id, playlist_id, playlist_item['id'], position)

        return response

    def check_playlist_membership(self, playlist_id):
        """
        Checks to see if the video is part of a given playlist as defined by the playlist_id. This method will always
        query the Youtube API directly.

        @param playlist_id:         The ID of the Youtube playlist to check for the video's membership
        @return:                    True if the video is part of the given playlist. False if not.
        """

        playlist = YoutubePlaylist(id=playlist_id, cache=self.cache)
        playlist.get_playlist_items()
        instances = []
        for item in playlist.videos:
            if item['contentDetails']['videoId'] == self.id:
                instances.append(item)
        logger.write("%i instance(s) found" % len(instances))

        if len(instances) > 0:
            self.cache.add_playlist_membership(
                vid_id=self.id,
                playlist_id=instances[0]['snippet']['playlistId'],
                playlist_item_id=instances[0]['id'],
                position=instances[0]['snippet']['position']
            )

            return instances
        else:
            self.cache.remove_playlist_membership(self.id, instances[0]['id'])

            return None

    def remove_duplicates(self, playlist_id):
        """
        Checks the specified playlist for the video, and if there are multiple instances of the video, it will remove
        all but the first

        @param playlist_id:         The ID of the Youtube playlist to check for the video's membership
        @return:                    True if the video is part of the given playlist. False if not.
        """
        instances = self.check_playlist_membership(playlist_id)
        removed = 0
        if len(instances) > 1:
            logger.write("Removing %i duplicate(s)" % (len(instances) - 1))
            while len(instances) > 1:
                request = self.client.client.playlistItems().delete(id=instances[-1]['id'])
                response = self.client.execute(request)
                instances.pop()
                removed += 1

        logger.write("%i duplicate(s) removed" % removed)

    def remove_from_playlist(self, playlist_id):
        """
        Removes the video from the specified playlist

        @param playlist_id: The ID of the Youtube playlist to check for the video's membership
        @return:            True if the video was part of a playlist and subsequently removed. False if not.
        """
        if self.check_playlist_membership(playlist_id):
            playlist_item_id = self.data['playlist_membership'][playlist_id]['playlist_item_id']

            params = {
                'id': playlist_item_id
            }
            request = self.client.client.playlistItems().delete(**params)
            response = self.client.execute(request)
            self.cache.remove_playlist_membership(self.id, playlist_id)

            logger.write("Removed from playlist: %s" % self.title)
            if playlist_id == self.data['current_playlist']:
                if len(self.data['playlist_membership']) > 0:
                    key = self.data['playlist_membership'].keys()[0]
                    self.data['current_playlist'] = self.data['playlist_membership'][key]
                else:
                    self.data['current_playlist'] = None

            return response
        else:
            return None

    def consolidate_playlist_membership(self, playlist_id):
        """
        This method will remove the video from all playlists it is in except one.

        @param playlist_id: The ID of the Youtube playlist that the video will be a member of.
                            The video will be removed from all other playlists
        @return:            None
        """
        for playlist in self.data['playlist_membership']:
            if playlist != playlist_id:
                self.remove_from_playlist(playlist)
            else:
                self.check_playlist_membership(playlist_id)