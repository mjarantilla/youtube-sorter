from handlers import client, utilities
import json

class YoutubePlaylist:
    def __init__(self, **kwargs):
        self.tier = kwargs['tier']
        self.id = kwargs['id']
        self.videos = []
        self.client = client.YoutubeClientHandler().get_client()

    def get_items(self):
        kwargs = {
            'playlistId': self.id,
            'maxResults': 50,
            'part': "snippet,contentDetails,id"
        }

        request = self.client.playlistItems().list(**kwargs)
        response = request.execute()
        self.videos = response['items']

        while 'nextPageToken' in response:
            kwargs['pageToken'] = response['nextPageToken']
            request = self.client.playlistItems().list(**kwargs)
            response = request.execute()
            self.videos = self.videos + response['items']

    def add_item(self, **kwargs):
        position = kwargs['position']
        previous_playlist = kwargs['previous_playlist'] if 'previous_playlist' in kwargs else None

        if previous_playlist is not None and previous_playlist != self.id:
            self.move_item(**kwargs)
        elif previous_playlist == self.id:
            self.change_item_position(**kwargs)
        else:
            self.insert_item(**kwargs)

    def delete_item(self, **kwargs):
        return None

    def move_item(self, **kwargs):
        return None

    def change_item_position(self, **kwargs):
        return None

    def insert_item(self, **kwargs):
        return None


class SubscribedChannel:
    def __init__(self, **kwargs):
        self.newest = []
        self.playlist_id = kwargs['playlist_id']
        config = utilities.ConfigHandler()
        self.records = json.load(open(config.records_filepath, mode='r'))

    def get_latest(self):
        youtube = client.YoutubeClientHandler()

        response = youtube.client.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=10,
            playlistId=self.playlist_id
        )

        response = youtube.execute(response)

        return response

    # def get_complete(self):

kwargs = {
    'playlist_id': 'UUMcVRw4Ix0g-Ek0WPyfnIWQ',
    'channel_id': 'UCMcVRw4Ix0g-Ek0WPyfnIWQ'
}
test_playlist = SubscribedChannel(**kwargs)
response = test_playlist.get_latest()
utilities.print_json(response)