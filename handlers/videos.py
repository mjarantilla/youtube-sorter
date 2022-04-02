from handlers.utilities import ConfigHandler, Logger, print_json
from handlers.client import YoutubeClientHandler
from handlers.playlist import YoutubePlaylist
import json

logger = Logger(tier=3)


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
        self.channel_name = self.data['snippet']['channelTitle']
        self.channel_id = self.data['snippet']['channelId']
        self.title = self.data['snippet']['title']
        self.metadata = None
        self.duration = self._get_duration()

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

    def _get_duration(self):
        duration = self.data['contentDetails']['duration'].replace("P", "").replace("T", "")
        days = 0
        hours = 0
        minutes = 0
        seconds = 0
        if 'D' in duration:
            days, duration = duration.split('D')
        if 'H' in duration:
            hours, duration = duration.split('H')
        if 'M' in duration:
            minutes, duration = duration.split('M')
        if 'S' in duration:
            seconds, duration = duration.split('S')

        hours = int(days) * 24 + int(hours)
        minutes = int(hours) * 60 + int(minutes)
        seconds = int(minutes) * 60 + int(seconds)

        return seconds

    def add_to_playlist(self, playlist_id, position=0, test=False):
        """
        Adds the video to the specified playlist at the specified position.

        @param playlist_id: The playlist ID of the destination playlist
        @param position:    The position at which to add the video to. Defaults to 0 (first position)
        @return:            The REST response
        """
        params = {
            'snippet.playlistId': playlist_id,
            'snippet.resourceId.kind': 'youtube#video',
            'snippet.resourceId.videoId': self.id,
            'snippet.position': position,
        }
        if not test:
            playlist_item = self.client.playlist_items_insert(params, part='snippet')
            self.data['playlist_membership'][playlist_id] = {
                'playlist_item_id': playlist_item['id'],
                'position': position
            }
            self.cache.add_playlist_membership(self.id, playlist_id, playlist_item['id'], position)

    def update_playlist_position(self, playlist_item_id, playlist_id, position=0, test=False):
        """
        Updates the video's position in the specified playlist to the specified position.

        @param playlist_id: The playlist ID of the destination playlist
        @param position:    The position at which to add the video to. Defaults to 0 (first position)
        @return:            The REST response
        """
        params = {
            'id':playlist_item_id,
            'snippet.playlistId': playlist_id,
            'snippet.resourceId.kind': 'youtube#video',
            'snippet.resourceId.videoId': self.id,
            'snippet.position': position,
        }
        if not test:
            playlist_item = self.client.playlist_item_update_position(params, part='snippet')
            self.data['playlist_membership'][playlist_id] = {
                'playlist_item_id': playlist_item['id'],
                'position': position
            }
            self.cache.add_playlist_membership(self.id, playlist_id, playlist_item['id'], position)

    def check_playlist_membership(self, playlist_id=None, playlist_handler=None, verify_only=False):
        """
        Checks to see if the video is part of a given playlist as defined by the playlist_id. This method will always
        query the Youtube API directly.

        @param playlist_id:         The ID of the Youtube playlist to check for the video's membership
        @return:                    True if the video is part of the given playlist. False if not.
        """

        assert playlist_id or playlist_handler, "Must pass either a playlist_id or playlist_handler"

        playlist = YoutubePlaylist(id=playlist_id, cache=self.cache, client=self.client) if playlist_handler is None else playlist_handler
        if len(playlist.videos) == 0:
            playlist.get_playlist_items()
        instances = []
        for item in playlist.videos:
            if item['contentDetails']['videoId'] == self.id:
                instances.append(item)
        # logger.write("%i instance(s) found of %s" % (len(instances), self.title))

        if len(instances) > 0:
            if not verify_only:
                self.cache.add_playlist_membership(
                    vid_id=self.id,
                    playlist_id=instances[0]['snippet']['playlistId'],
                    playlist_item_id=instances[0]['id'],
                    position=instances[0]['snippet']['position']
                )

        else:
            if not verify_only:
                self.cache.remove_playlist_membership(self.id, playlist_id)

        return instances

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

    def remove_from_playlist(self, playlist_id=None, playlist_item_id=None, already_checked=True, test=False):
        """
        Removes the video from the specified playlist

        @param playlist_id: The ID of the Youtube playlist to check for the video's membership
        @return:            True if the video was part of a playlist and subsequently removed. False if not.
        """
        assert playlist_id or playlist_item_id, "Either playlist_id or playlist_item_id needs to be specified"

        if playlist_item_id:
            params = {
                'id': playlist_item_id
            }
            response = None
            if not test:
                request = self.client.client.playlistItems().delete(**params)
                response = self.client.execute(request)
                self.cache.remove_playlist_membership(self.id, playlist_id)

            logger.write("Removed from playlist: %s" % self.title)

            return response

        if not already_checked:
            already_checked = self.check_playlist_membership(playlist_id)
        if already_checked:
            if playlist_id:
                if playlist_id in self.data['playlist_membership']:
                    playlist_item_id = self.data['playlist_membership'][playlist_id]['playlist_item_id']

                    params = {
                        'id': playlist_item_id
                    }
                    response = None
                    if not test:
                        request = self.client.client.playlistItems().delete(**params)
                        response = self.client.execute(request)
                        self.cache.remove_playlist_membership(self.id, playlist_id)

                    logger.write("Removed from playlist: %s" % self.title)

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