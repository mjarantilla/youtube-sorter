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


class Records:
    def __init__(self):
        config = utilities.ConfigHandler()
        self.filepath = config.records_filepath
        self.data = json.load(open(self.filepath, mode='r'))
        utilities.print_json(self.data)

    def write_records(self):
        utilities.Logger().write("Writing records.json")
        fp = open(self.filepath, mode='w')
        utilities.print_json(self.data, fp=fp)
        fp.close()


class SubscribedChannel:
    def __init__(self, **kwargs):
        self.newest = []
        self.playlist_id = kwargs['playlist_id']
        self.channel_id = kwargs['channel_id']
        config = utilities.ConfigHandler()
        records = Records()
        if self.channel_id not in records.data:
            records.data[self.channel_id] = self.get_last()
            records.write_records()
        self.latest_video_id = records.data[self.channel_id]

    def get_last(self):
        utilities.Logger().write("Getting most recently uploaded video")
        youtube = client.YoutubeClientHandler()

        request = youtube.client.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=1,
            playlistId=self.playlist_id
        )
        response = youtube.execute(request)

        for item in response['items']:
            return item['contentDetails']['videoId']

    def get_latest(self):
        utilities.Logger().write("Getting latest videos")
        youtube = client.YoutubeClientHandler()

        request = youtube.client.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=self.playlist_id
        )

        response = youtube.execute(request)
        # latest_found = False
        # next_page_token = response['nextPageToken'] if 'nextPageToken' in response else None
        # while not latest_found:
        #     for item in response['items']:
        #         if item['contentDetails']['videoId'] != self.latest_video_id:
        #             self.newest.append(item)
        #         else:
        #             latest_found = True
        #
        # utilities.print_json(self.get_last())

        return results

    # def get_complete(self):

kwargs = {
    'playlist_id': 'UUiDJtJKMICpb9B1qf7qjEOA',
    'channel_id': 'UCiDJtJKMICpb9B1qf7qjEOA'
}
test_playlist = SubscribedChannel(**kwargs)
response = test_playlist.get_latest()
for item in response:
    print(item['snippet']['title'])
# input()
# for item in response['items']:
#     print(item['snippet']['position'], item['snippet']['title'], item['snippet']['publishedAt'], sep="\t")