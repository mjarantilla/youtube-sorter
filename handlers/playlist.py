from handlers import client, utilities
import json
from datetime import datetime
from handlers.utilities import Logger

logger = Logger()


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
        self.youtube_date_format = config.variables['YOUTUBE_DATE_FORMAT']
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

    def write_records(self):
        utilities.Logger().write("Writing records.json")
        fp = open(self.filepath, mode='w')
        utilities.print_json(self.data, fp=fp)
        fp.close()

    def update_latest(self, vid_data):
        record = {
            'videoId': vid_data['snippet']['resourceId']['videoId'],
            'publishedAt': vid_data['snippet']['publishedAt'],
            'channelId': vid_data['snippet']['channelId'],
            'channelTitle': vid_data['snippet']['channelTitle'],
            'title': vid_data['snippet']['title']
        }
        current_latest = self.latest_videos[record['channelId']] if record['channelId'] in self.latest_videos else None

        if self.is_newer(current_latest['publishedAt'], record['publishedAt']):
            self.latest_videos[record['channelId']] = {
                'videoId': record['videoId'],
                'publishedAt': record['publishedAt']
            }
            self.write_records()

    def is_newer(self, current, newer):
        tmp_current = datetime.strptime(current, self.youtube_date_format)
        tmp_newer = datetime.strptime(newer, self.youtube_date_format)
        if tmp_newer > tmp_current:
            return True
        else:
            return False

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
        self.playlist_id = kwargs['uploads']
        self.channel_id = kwargs['id']
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
        Records().update_latest(items[0])

    def get_latest(self, all=False):
        logger.write("Getting latest videos")
        latest_videos = Records().latest_videos
        last_video_recorded = latest_videos[self.channel_id] if self.channel_id in latest_videos else {}
        youtube = client.YoutubeClientHandler()

        request = youtube.client.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=self.playlist_id
        )

        response = youtube.execute(request)

        items = response['items']

        pages = 1
        if all:
            while 'nextPageToken' in response:
                request = youtube.client.playlistItems().list(
                    part="snippet",
                    maxResults=50,
                    playlistId=self.playlist_id,
                    pageToken=response['nextPageToken']
                )
                response = youtube.execute(request)
                items = items + response['items']
                pages += 1
            Records().update_latest(items[0])
        logger.write("Pages of videos: %i" % pages)
        logger.write("Videos fetched: %i" % len(items))

        items = sorted(items, reverse=True, key=lambda x: x['snippet']['publishedAt'])

        # for item in items:
        #

        return items

