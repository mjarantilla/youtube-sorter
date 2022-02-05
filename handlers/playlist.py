from handlers import client, utilities, ranks
import json
from time import sleep
from datetime import datetime, timedelta
from handlers.utilities import Logger, print_json
import googleapiclient.errors
import threading
import copy

logger = Logger()


class YoutubePlaylist:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.videos = []
        self.client = client.YoutubeClientHandler().get_client()
        self.cache_filepath = kwargs['cache_filepath']

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

    def write_cache(self, cache_filepath=None):
        if cache_filepath is None:
            cache_filepath = self.cache_filepath

        cache_fp = open(cache_filepath, mode='w')
        print_json(self.videos, fp=cache_fp)
        cache_fp.close()

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

    def add_record(self, vid_data):
        record = {
            'videoId': vid_data['id'],
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
        self.oldest_date = kwargs['oldest_date']

    def get_latest(self, all=False):
        logger.write("Getting latest videos: %s" % self.name)
        youtube = client.YoutubeClientHandler()

        request = youtube.client.playlistItems().list(
            part="contentDetails",
            maxResults=50,
            playlistId=self.playlist_id
        )

        response = youtube.execute(request)

        items = response['items']

        pages = 1
        if all:
            while 'nextPageToken' in response:
                request = youtube.client.playlistItems().list(
                    part="contentDetails",
                    maxResults=50,
                    playlistId=self.playlist_id,
                    pageToken=response['nextPageToken']
                )
                response = youtube.execute(request)
                items = items + response['items']
                pages += 1
        logger.write("Pages of videos for %s: %i" % (self.name, pages))
        logger.write("Videos fetched for %s: %i" % (self.name, len(items)))

        request_list = [
            []
        ]
        counter = 0
        total = 0
        page = 0
        results = []
        for item in items:
            vid_id = item['contentDetails']['videoId']
            published_date = str(item['contentDetails']['videoPublishedAt']).split('.')[0].replace("Z", "")+".0"
            record = {
                'videoId': vid_id,
                'publishedAt': datetime.strptime(published_date, self.date_format),
                'channelId': self.channel_id
            }
            if self.vid_is_valid(record):
                request_list[page].append(vid_id)
                counter += 1
                total += 1
            if counter == 50:
                counter = 0
                request_list.append([])
                page += 1

        logger.write("Videos requiring additional details for %s: %i" % (self.name, total))

        page_num = 0
        threads = []
        for page_list in request_list:
            id_list = ",".join(page_list)
            kwargs = {
                "part": "snippet",
                "id": id_list
            }
            page_id = "%s Page %i" % (self.name, page_num)
            page_num += 1
            request = RequestThreader(page_id=page_id, request_kwargs=kwargs)
            threads.append(request)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        for thread in threads:
            # response = thread.response
            # request = youtube.client.videos().list(**kwargs)
            # response = youtube.execute(request)
            results += thread.response['items']

        for vid_details in results:
            vid_details['snippet']['publishedAt'] = self.correct_date_format(vid_details['snippet']['publishedAt'])

        results = sorted(results, reverse=True, key=lambda x: x['snippet']['publishedAt'])
        self.newest = results

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

    def vid_is_valid(self, record):
        if record['publishedAt'] > self.oldest_date:
            if record['videoId'] not in self.records.channel_vids_added(record['channelId']):
                return True
        return False


class RequestThreader(threading.Thread):
    def __init__(self, page_id, request_kwargs):
        super().__init__()
        self.kwargs = request_kwargs
        self.name = page_id
        self.response = None

    def run(self):
        logger.write("Starting RequestThreader thread: %s" % self.name)
        youtube = client.YoutubeClientHandler()
        request = youtube.client.videos().list(**self.kwargs)
        self.response = youtube.execute(request)


class QueueHandler(YoutubePlaylist):
    def __init__(self):
        config = utilities.ConfigHandler()
        super().__init__(
            id=config.variables['QUEUE_ID']
        )
        self.ranks = ranks.RanksHandler()
        self.subscriptions = json.load(open(config.subscriptions_filepath, mode='r'))
        self.channel_details = self.subscriptions['details']
        self.records = Records()
        days_to_search = config.variables['DAYS_TO_SEARCH']
        self.date_format = config.variables['YOUTUBE_DATE_FORMAT']
        self.oldest_date = datetime.now() - timedelta(days=days_to_search)
        logger.write(self.oldest_date.strftime(config.variables['EVENT_LOG_FORMAT']))

    def scan_ordered_channels(self, rank_order=None):
        if rank_order is None:
            rank_order = ['f1', 'primary', 'secondary']
        channel_names = []
        rank_data = self.ranks.define_ranks()
        for rank in rank_order:
            logger.write("Scanning %s" % rank)
            for rank_block in rank_data:
                if rank_block.name == rank:
                    channel_names += rank_block.get_channels()

        self.scan_channels(channel_names=channel_names)

    def scan_channels(self, all_videos=False, channel_names=None):
        def find_tier_queue_id(channel):
            tier_name = ""
            handler = self.ranks
            handler.define_ranks()
            for tier in handler.rank_data:
                tier_name = tier.name
                tier_channels = tier.get_channels()
                if channel in tier_channels:
                    break

            if tier_name not in handler.queues:
                logger.write("- %s: default" % channel)
                return handler.queues['queue']
            else:
                logger.write("- %s: %s" % (channel, tier_name))
                return handler.queues[tier_name]

        added_to_queue = []
        threads = []
        if channel_names is None:
            channel_details = self.channel_details
        else:
            channel_details = {}
            for channel_name in channel_names:
                if channel_name in self.channel_details:
                    channel_details[channel_name] = self.channel_details[channel_name]

        batch = []
        for channel_name in channel_details:
            tier_queue_id = find_tier_queue_id(channel_name)
            if tier_queue_id is None:
                tier_queue_id = self.id

            kwargs = channel_details[channel_name]
            kwargs['name'] = channel_name
            if not self.ranks.channel_filtered(channel_id=kwargs['id']):
                # added_to_queue = added_to_queue + self.scan_channel(all=all_videos, **kwargs)
                thread_kwargs = {
                    "queue_id": tier_queue_id,
                    "name": channel_name,
                    "oldest_date": self.oldest_date,
                    "records": self.records,
                    "channel_kwargs": kwargs,
                    "all": all_videos
                }
                batch.append(ChannelScanner(**thread_kwargs))
            if len(batch) > 10:
                threads.append(batch.copy())
                batch = []
                logger.write("Batch %i written" % len(threads))
        threads.append(batch.copy())
        logger.write("Batch %i written" % len(threads))

        batch_count = 0
        for batch in threads:
            logger.write("Processing Batch %i" % batch_count)
            for thread in batch:
                logger.write("- %s" % thread.name)

            for thread in batch:
                thread.start()
                sleep(0.1)

            for thread in batch:
                thread.join()

            logger.write("\n\n\n")

            batch_count += 1
            logger.write("All batches done.")

        for batch in threads:
            for thread in batch:
                added_to_queue += thread.added_to_queue

        if len(added_to_queue) > 0:
            logger.write("Added to queue:")
            for vid_data in added_to_queue:
                logger.write("\t- %s: %s" % (vid_data['snippet']['channelTitle'], vid_data['snippet']['title']))
                # self.records.add_record(vid_data)

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


class ChannelScanner(threading.Thread):
    def __init__(self, queue_id, name, oldest_date, records, channel_kwargs, all):
        super().__init__()
        self.queue_id = queue_id
        self.name = name
        self.added_to_queue = []
        self.oldest_date = oldest_date
        self.records = records
        self.channel_kwargs = channel_kwargs
        channel_kwargs['oldest_date'] = self.oldest_date
        self.all = all

    def run(self):
        logger.write("Starting thread: %s" % self.name)
        channel = SubscribedChannel(**self.channel_kwargs)
        channel.get_latest(all=self.all)
        self.added_to_queue = []
        for vid_data in channel.newest:
            record = {
                'videoId': vid_data['id'],
                'publishedAt': vid_data['snippet']['publishedAt'],
                'channelId': vid_data['snippet']['channelId'],
                'channelTitle': vid_data['snippet']['channelTitle'],
                'title': vid_data['snippet']['title']
            }

            if 'liveBroadcastContent' in vid_data['snippet']:
                record['liveBroadcastContent'] = vid_data['snippet']['liveBroadcastContent']

            valid = self.vid_is_valid(record)
            if valid:
                fp = open('./logs/snippets.log', mode='a')
                tmp_vid_data = copy.deepcopy(vid_data)
                tmp_vid_data['snippet']['publishedAt'] = tmp_vid_data['snippet']['publishedAt'].strftime("%Y-%m-%dT%H:%M:%S.%f")
                utilities.print_json(tmp_vid_data, fp)
                fp.close()

                self.add_video_to_queue(vid_data)
                self.added_to_queue.append(vid_data)

        return self.added_to_queue

    def add_video_to_queue(self, vid_data):
        youtube = client.YoutubeClientHandler()
        body = {
            'snippet': {
                'playlistId': self.queue_id,
                'resourceId': {
                    'kind': "youtube#video",
                    'videoId': vid_data['id']
                }
            }
        }
        try:
            logger.write(
                "Adding to queue: %s - %s" % (vid_data['snippet']['channelTitle'], vid_data['snippet']['title']))
            request = youtube.client.playlistItems().insert(part='snippet', body=body)
            response = youtube.execute(request)
            self.records.add_record(vid_data=vid_data)
        except googleapiclient.errors.HttpError as e:
            print(e.content)
            print(e.error_details)
            print(e.resp)
            raise
        except:
            raise

        return response

    def vid_is_valid(self, record):
        if record['publishedAt'] > self.oldest_date:
            if record['videoId'] not in self.records.channel_vids_added(record['channelId']):
                tmp_record = {
                    'title': record['title'],
                    'channelTitle': record['channelTitle']
                }
                if 'liveBroadcastContent' in tmp_record:
                    tmp_record['liveBroadcastContent'] = record['liveBroadcastContent']
                if 'liveBroadcastContent' in record:
                    if record['liveBroadcastContent'] == 'none':
                        return True
                    else:
                        logger.write("NOT YET PUBLISHED: %s - %s" % (record['channelTitle'], record['title']))
                else:
                    return True
        return False
