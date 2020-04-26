from handlers import client, utilities
import json
from datetime import datetime

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
        self.date = datetime.now().strftime(config.variables['DATE_FORMAT'])
        self.filepath = config.records_filepath
        self.data = json.load(open(self.filepath, mode='r'))
        if 'dates' not in self.data:
            self.data['dates'] = {
                'previously_added': {}
            }
        if 'latest' not in self.data:
            self.data['latest'] = {}
        self.videos_added = self.data['dates']
        self.latest_videos = self.data['latest']
        utilities.print_json(self.data)

    def write_records(self):
        utilities.Logger().write("Writing records.json")
        fp = open(self.filepath, mode='w')
        utilities.print_json(self.data, fp=fp)
        fp.close()

    def update_latest(self, vid_data):
        record = {
            'videoId': vid_data['snippet']['resourceId']['videoId'],
            'PublishedAt': vid_data['snippet']['publishedAt'],
            'channelId': vid_data['snippet']['channelId'],
            'channelTitle': vid_data['snippet']['channelTitle'],
            'title': vid_data['snippet']['title']
        }

        self.latest_videos[record['channelId']] = record['videoId']
        self.write_records()

    def add_record(self, vid_data):
        record = {
            'videoId': vid_data['snippet']['resourceId']['videoId'],
            'PublishedAt': vid_data['snippet']['publishedAt'],
            'channelId': vid_data['snippet']['channelId'],
            'channelTitle': vid_data['snippet']['channelTitle'],
            'title': vid_data['snippet']['title']
        }

        self.videos_added[self.date][record['video_id']] = record
        self.write_records()


class SubscribedChannel:
    def __init__(self, **kwargs):
        self.newest = []
        self.playlist_id = kwargs['playlist_id']
        self.channel_id = kwargs['channel_id']
        config = utilities.ConfigHandler()

    def get_last(self):
        utilities.Logger().write("Getting most recently uploaded video")
        youtube = client.YoutubeClientHandler()

        request = youtube.client.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=self.playlist_id
        )
        response = youtube.execute(request)

        items = sorted(response['items'], reverse=True, key=lambda x: x['snippet']['publishedAt'])
        records = Records()
        records.update_latest(items[0])

    def get_latest(self):
        utilities.Logger().write("Getting latest videos")
        youtube = client.YoutubeClientHandler()

        request = youtube.client.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=self.playlist_id
        )

        response = youtube.execute(request)

        items = sorted(response['items'], reverse=True, key=lambda x: x['snippet']['publishedAt'])

        found_latest = False
        # for item in items:

        return items

    # def get_complete(self):

