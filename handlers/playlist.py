from handlers import client, utilities, ranks
import json
from datetime import datetime, timedelta
from handlers.utilities import Logger
import googleapiclient.errors

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
        fp = open(self.filepath, mode='w')
        utilities.print_json(self.data, fp=fp)
        fp.close()

    def channel_vids_added(self, channel_id):
        channel_video_ids = {}
        for date in self.videos_added:
            if channel_id in self.videos_added[date]:
                for vid_id in self.videos_added[date][channel_id]:
                    channel_video_ids[vid_id] = self.videos_added[date][channel_id][vid_id]

        return channel_video_ids

    # def update_latest(self, vid_data):
    #     record = {
    #         'videoId': vid_data['snippet']['resourceId']['videoId'],
    #         'publishedAt': vid_data['snippet']['publishedAt'],
    #         'channelId': vid_data['snippet']['channelId'],
    #         'channelTitle': vid_data['snippet']['channelTitle'],
    #         'title': vid_data['snippet']['title']
    #     }
    #     current_latest = self.latest_videos[record['channelId']] if record['channelId'] in self.latest_videos else None
    #
    #     if self.is_newer(current_latest['publishedAt'], record['publishedAt']):
    #         self.latest_videos[record['channelId']] = {
    #             'videoId': record['videoId'],
    #             'publishedAt': record['publishedAt']
    #         }
    #         self.write_records()

    # def is_newer(self, current, newer):
    #     tmp_current = datetime.strptime(current, self.youtube_date_format)
    #     tmp_newer = datetime.strptime(newer, self.youtube_date_format)
    #     if tmp_newer > tmp_current:
    #         return True
    #     else:
    #         return False

    def add_record(self, vid_data):
        record = {
            'videoId': vid_data['snippet']['resourceId']['videoId'],
            'publishedAt': vid_data['snippet']['publishedAt'].strftime(self.youtube_date_format),
            'channelId': vid_data['snippet']['channelId'],
            'channelTitle': vid_data['snippet']['channelTitle'],
            'title': vid_data['snippet']['title']
        }

        if self.date not in self.videos_added:
            self.videos_added[self.date] = {}
        if record['channelId'] not in self.videos_added[self.date]:
            self.videos_added[self.date][record['channelId']] = {}
        self.videos_added[self.date][record['channelId']][record['videoId']] = record
        self.write_records()


class LegacyRecords(Records):
    def __init__(self, legacy_filepath=None):
        super().__init__()
        config = utilities.ConfigHandler()
        self.legacy_filepath = config.records_filepath + ".legacy" if legacy_filepath is None \
            else legacy_filepath
        self.legacy_data = json.load(open(self.legacy_filepath, mode='r'))
        self.videos_added = self.import_legacy()

    def import_legacy(self):
        new_json = {}
        for date in self.legacy_data:
            new_json[date] = {}
            for vid_id in self.legacy_data[date]:
                vid_data = self.legacy_data[date][vid_id]
                channel_id = vid_data['channelId']
                if channel_id not in new_json[date]:
                    new_json[date][channel_id] = {}
                new_json[date][channel_id][vid_id] = vid_data
        return new_json

    def combine_data(self):
        new_json = {}
        for data_source in [self.data['dates'], self.import_legacy()]:
            for date in data_source:
                if date not in new_json:
                    new_json[date] = {}
                for channel_id in data_source[date]:
                    if channel_id not in new_json[date]:
                        new_json[date][channel_id] = {}
                    for vid_id in data_source[date][channel_id]:
                        new_json[date][channel_id][vid_id] = data_source[date][channel_id][vid_id]

        self.data['dates'] = new_json


class SubscribedChannel:
    def __init__(self, **kwargs):
        self.newest = []
        self.name = kwargs['name']
        self.playlist_id = kwargs['uploads']
        self.channel_id = kwargs['id']
        self.records = Records()
        config = utilities.ConfigHandler()
        self.queue_id = config.variables['QUEUE_ID']
        self.date_format = config.variables['YOUTUBE_DATE_FORMAT']

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
        logger.write("Getting latest videos: %s" % self.name)
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
            logger.write("Pages of videos: %i" % pages)
            logger.write("Videos fetched: %i" % len(items))

        items = sorted(items, reverse=True, key=lambda x: x['snippet']['publishedAt'])
        for item in items:
            item['snippet']['publishedAt'] = self.correct_date_format(item['snippet']['publishedAt'])

        self.newest = items

        # for item in items:
        #     if self.records.is_newer(last_video_recorded['publishedAt'], item['snippet']['publishedAt']):
        #         self.newest.append(item)
        #     else:
        #         break

    def correct_date_format(self, published):
        if 'Z' in published:
            published = published[:-1]
        if '.' in published:
            published_date = datetime.strptime(published, self.date_format)
        else:
            modified_date_format = self.date_format[:-3]
            published_date = datetime.strptime(published, modified_date_format)

        return published_date


class QueueHandler:
    def __init__(self):
        config = utilities.ConfigHandler()
        self.id = config.variables['QUEUE_ID']
        self.ranks = ranks.RanksHandler()
        self.subscriptions = json.load(open(config.subscriptions_filepath, mode='r'))
        self.channel_details = self.subscriptions['details']
        self.records = Records()
        days_to_search = config.variables['DAYS_TO_SEARCH']
        self.date_format = config.variables['YOUTUBE_DATE_FORMAT']
        self.oldest_date = datetime.now() - timedelta(days=days_to_search)

    def scan_all_channels(self, all=False):
        added_to_queue = []
        for channel_name in self.channel_details:
            kwargs = self.channel_details[channel_name]
            kwargs['name'] = channel_name
            if not self.ranks.channel_filtered(channel_id=kwargs['id']):
                added_to_queue = added_to_queue + self.scan_channel(all=all, **kwargs)

        if len(added_to_queue) > 0:
            logger.write("Added to queue:")
            for record in added_to_queue:
                logger.write("\t- %s: %s" % (record['channelTitle'], record['title']))

    def scan_channel(self, all=False, **kwargs):
        channel = SubscribedChannel(**kwargs)
        channel.get_latest(all=all)
        added_to_queue = []
        for vid_data in channel.newest:
            record = {
                'videoId': vid_data['snippet']['resourceId']['videoId'],
                'publishedAt': vid_data['snippet']['publishedAt'],
                'channelId': vid_data['snippet']['channelId'],
                'channelTitle': vid_data['snippet']['channelTitle'],
                'title': vid_data['snippet']['title']
            }
            valid = self.vid_is_valid(record)
            if valid:
                self.add_video_to_queue(vid_data)
                added_to_queue.append(record)

        return added_to_queue

    def vid_is_valid(self, record):
        if record['publishedAt'] > self.oldest_date:
            if record['videoId'] not in self.records.channel_vids_added(record['channelId']):
                return True
            else:
                return False
        return False

    def add_video_to_queue(self, vid_data):
        youtube = client.YoutubeClientHandler()
        body = {
            'snippet': {
                'playlistId': self.id,
                'resourceId': {
                    'kind': vid_data['snippet']['resourceId']['kind'],
                    'videoId': vid_data['snippet']['resourceId']['videoId']
                }
            }
        }
        try:
            logger.write(
                "Adding to queue: %s - %s" % (vid_data['snippet']['channelTitle'], vid_data['snippet']['title']))
            request = youtube.client.playlistItems().insert(part='snippet', body=body)
            response = youtube.execute(request)
            # self.records.update_latest(vid_data)
            self.records.add_record(vid_data)
        except googleapiclient.errors.HttpError as e:
            print(e.content)
            print(e.error_details)
            print(e.resp)
            raise

        return response