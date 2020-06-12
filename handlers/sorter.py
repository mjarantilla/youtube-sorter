from handlers import client, utilities, ranks


class YoutubePlaylist:
    def __init__(self, **kwargs):
        self.tier = kwargs['tier']
        self.id = kwargs['id']
        self.videos = []
        self.client = client.YoutubeClientHandler().get_client()
        self.new_items_queue = []
        self.deleted_items_queue = []
        self.backlog = []

    def get_items(self):
        kwargs = {
            'playlistId': self.id,
            'maxResults': 50,
            'part': "snippet,contentDetails,id"
        }

        request = self.client.playlistItems().list(**kwargs)
        response = request.execute()
        items = response['items']

        while 'nextPageToken' in response:
            kwargs['pageToken'] = response['nextPageToken']
            request = self.client.playlistItems().list(**kwargs)
            response = request.execute()
            items = items + response['items']

        self.videos = items

    def sort(self):
        ranks_handler = ranks.RanksHandler()
        ordered_channel_ids = ranks_handler.get_ordered_channels(self.tier)


class SortHandler:
    def __init__(self, **kwargs):
        config = utilities.ConfigHandler()
        self.ranks = ranks.RanksHandler()
