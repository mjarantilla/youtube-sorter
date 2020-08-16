from handlers import client, utilities, ranks
from copy import deepcopy
import threading


class YoutubePlaylist(threading.Thread):
    def __init__(self, name, playlist_type, playlist_id=None, **kwargs):
        # Expected kwargs:
        # - name
        # - id (optional)

        super().__init__()
        self.ranks = ranks.RanksHandler()
        self.config = utilities.ConfigHandler()
        self.client = client.YoutubeClientHandler().get_client()
        self.name = name

        # Sets playlist ID to what is submitted as a kwarg.
        # If no ID is set in kwarg, look up playlist ID by name in ranks.json.
        # If no ID is present in ranks.json, throw an error.
        self.id = playlist_id
        self.types = {
            'primary': self.ranks.playlists,
            'backlog': self.ranks.backlogs,
            'queue': self.ranks.queues
        }
        if self.id is None and self.name in self.types[playlist_type]:
            self.id = self.types[playlist_type][self.name]
        if self.id is None:
            raise ValueError("Invalid playlist '%s'; no playlist ID supplied" % self.name)

        # Resources to use internally
        self.ordered_channels = []
        self.videos = []
        self.queue = []
        self.playlist_items_to_change = {}
        self.test = kwargs['test'] if 'test' in kwargs else False

    def get_items(self, id=None):
        assign_self_videos = True if id is None else False
        if id is None:
            id = self.id
        kwargs = {
            'playlistId': id,
            'maxResults': 50,
            'part': "snippet"
        }

        request = self.client.playlistItems().list(**kwargs)
        response = request.execute()
        items = response['items']

        while 'nextPageToken' in response:
            kwargs['pageToken'] = response['nextPageToken']
            request = self.client.playlistItems().list(**kwargs)
            response = request.execute()
            items = items + response['items']

        vid_ids = []
        vid_data = {}
        for item in items:
            vid_data[item['snippet']['resourceId']['videoId']] = {
                "playlist_data": deepcopy(item)
            }
            vid_ids.append(item['snippet']['resourceId']['videoId'])

        id_list = ",".join(vid_ids)
        kwargs = {
            "part": "snippet,contentDetails",
            "id": id_list,
            "maxResults": 50
        }
        request = self.client.videos().list(**kwargs)
        response = request.execute()
        items = response['items']

        while 'nextPageToken' in response:
            kwargs['pageToken'] = response['nextPageToken']
            request = self.client.videos().list(**kwargs)
            response = request.execute()
            items = items + response['items']

        for item in items:
            vid_data[item['id']]['vid_data'] = deepcopy(item)

        if assign_self_videos:
            self.videos = vid_data
        return vid_data

    def get_ordered_channels(self, tier_name=None):
        def add_subtier_channels(playlist_name, tier_data):
            subtier_channels = []
            tier = tier_data['tier']
            if 'playlist_id' in tier_data:
                if tier_data['playlist_id'] == playlist_name:
                    if 'channels' in tier_data:
                        for channel_name in tier_data['channels']:
                            subtier_channels.append(channel_name)
            if 'subtiers' in tier_data:
                counter = 0
                for subtier_data in tier_data['subtiers']:
                    if 'tier' not in subtier_data:
                        subtier_data['tier'] = "%s_%s" % (tier, str(counter).zfill(2))
                    if 'playlist_id' in tier_data and 'playlist_id' not in subtier_data:
                        subtier_data['playlist_id'] = tier_data['playlist_id']
                    subtier_channels += add_subtier_channels(playlist_name, subtier_data)

            self.ordered_channels = subtier_channels
            return subtier_channels

        handler = ranks.RanksHandler()
        channel_names = []
        for tier in handler.ranks:
            channel_names += add_subtier_channels(
                playlist_name=self.name if tier_name is None else tier_name,
                tier_data=tier
            )
        channels = []
        for channel_name in channel_names:
            print(channel_name)
            if channel_name in handler.subscriptions:
                channel_details = handler.subscriptions[channel_name]
                channel_id = channel_details['id']
                channels.append(
                    {
                        'name': channel_name,
                        'id': channel_id
                    }
                )
        return channels

    def get_channel_lists(self):
        channels = self.get_ordered_channels()

        channel_videos = {}
        for channel in channels:
            channel_videos[channel['id']] = []

        return channel_videos

    def sort(self, videos):
        channels = self.get_ordered_channels()
        channel_lists = self.get_channel_lists()

        for vid_id in sorted(videos, key=lambda x: videos[x]['vid_data']['snippet']['publishedAt']):
            video = videos[vid_id]
            channel_id = video['vid_data']['snippet']['channelId']
            if channel_id in channel_lists:
                channel_lists[channel_id].append(video)

        video_list = []
        video_dict = {}
        index = 0
        for channel in channels:
            for video in channel_lists[channel['id']]:
                video['playlist_data']['snippet']['position'] = index
                vid_id = video['vid_data']['id']
                video_list.append(video)
                video_dict[vid_id] = deepcopy(video)
                index += 1

        return video_dict

    def sort_playlist(self, import_queue=False):
        total = deepcopy(self.videos)
        total_sorted = self.sort(total)
        playlist_items_to_change = {}

        for vid_id in sorted(total_sorted, key=lambda x: total_sorted[x]['playlist_data']['snippet']['position']):
            new_pos = total_sorted[vid_id]['playlist_data']['snippet']['position']
            vid_data = self.videos[vid_id] if vid_id not in self.queue else self.queue[vid_id]
            title = vid_data['vid_data']['snippet']['title']
            if vid_id in self.queue:
                vid_data = self.queue[vid_id]
                vid_data['playlist_data']['snippet']['destinationPlaylistId'] = self.id
                vid_data['playlist_data']['snippet']['position'] = new_pos
                playlist_items_to_change[vid_id] = deepcopy(vid_data)
                self.videos = deepcopy(self.modify_pos(deepcopy(self.videos), vid_id, title, new_pos, True))
            else:
                old_pos = vid_data['playlist_data']['snippet']['position']
                total_sorted[vid_id]['playlist_data']['snippet']['oldPosition'] = old_pos
                if new_pos != old_pos:
                    playlist_items_to_change[vid_id] = deepcopy(total_sorted[vid_id])
                    self.videos = deepcopy(self.modify_pos(deepcopy(self.videos), vid_id, title, new_pos))

        self.playlist_items_to_change = deepcopy(playlist_items_to_change)

        return total_sorted

    def commit_sort(self):
        playlist_items = self.playlist_items_to_change
        for vid_id in sorted(playlist_items, key=lambda x: playlist_items[x]['playlist_data']['snippet']['position']):
            vid_data = playlist_items[vid_id]
            pos = vid_data['playlist_data']['snippet']['position']

            if 'destinationPlaylistId' in vid_data['playlist_data']['snippet']:
                self.transfer_playlist_item(vid_data=vid_data, vid_id=vid_id, old_playlist='queue', position=pos)
            else:
                self.update_playlist_item_position(vid_data=vid_data, vid_id=vid_id, position=pos)

    def modify_pos(self, videos, video_id, title, new_pos, add=False):
        new_videolist = deepcopy(videos)
        if not add:
            old_pos = videos[video_id]['playlist_data']['snippet']['position']

            for vid_id in sorted(videos, key=lambda x: videos[x]['playlist_data']['snippet']['position']):
                vid_data = new_videolist[vid_id]
                video_position = vid_data['playlist_data']['snippet']['position']
                if vid_id != video_id:
                    if new_pos > old_pos and new_pos > video_position >= old_pos:
                        vid_data['playlist_data']['snippet']['position'] -= 1
                    elif new_pos < old_pos and new_pos <= video_position < old_pos:
                        vid_data['playlist_data']['snippet']['position'] += 1
                    else:
                        vid_data['playlist_data']['snippet']['position'] = vid_data['playlist_data']['snippet']['position']
                else:
                    vid_data['playlist_data']['snippet']['position'] = new_pos
        else:
            for vid_id in sorted(videos, key=lambda x: videos[x]['playlist_data']['snippet']['position']):
                vid_data = new_videolist[vid_id]
                video_position = vid_data['playlist_data']['snippet']['position']
                if video_position >= new_pos:
                    vid_data['playlist_data']['snippet']['position'] += 1

        return new_videolist

    def transfer_playlist_item(self, vid_data, vid_id, old_playlist, position=None):
        channel = vid_data['vid_data']['snippet']['channelTitle']
        title = vid_data['vid_data']['snippet']['title']
        pos = "end" if position is None else "position %i" % position
        print("Adding %s: %s to '%s' playlist to %s from %s" % (channel, title, self.name, pos, old_playlist))
        body = {
            'snippet': {
                'playlistId': self.id,
                'resourceId': {
                    'kind': "youtube#video",
                    'videoId': vid_id
                }
            }
        }

        if position is not None:
            body["snippet"]["position"] = position

        insert_request = self.client.playlistItems().insert(part="snippet", body=body)
        delete_request = self.client.playlistItems().delete(id=vid_data['playlist_data']['id'])

        if not self.test:
            insert_response = insert_request.execute()
            delete_response = delete_request.execute()

            return {
                'insert_response': insert_response,
                'delete_response': delete_response
            }
        else:
            print("Would have executed, but currently in test mode")

    def update_playlist_item_position(self, vid_data, vid_id, position=None):
        channel = vid_data['vid_data']['snippet']['channelTitle']
        title = vid_data['vid_data']['snippet']['title']
        pos = "end" if position is None else "position %i" % position
        playlist_item_id = vid_data['playlist_data']['id']
        old_pos = vid_data['playlist_data']['snippet']['oldPosition']
        print("Moving %s: %s to %s from position %i" % (channel, title, pos, old_pos))
        body = {
            "id": playlist_item_id,
            'snippet': {
                'playlistId': self.id,
                'resourceId': {
                    'kind': "youtube#video",
                    'videoId': vid_id
                }
            }
        }
        if position is not None:
            body["snippet"]["position"] = position

        update_request = self.client.playlistItems().update(part="snippet", body=body)
        if not self.test:
            response = update_request.execute()
            return response
        else:
            print("Would have executed, but currently in test mode")

    def delete_playlist_item(self, id):
        delete_request = self.client.playlistItems().delete(id)
        if not self.test:
            delete_response = delete_request.execute()
            return delete_response
        else:
            print("Would have executed, but currently in test mode")

    def run(self):
        return None


class PrimaryPlaylist(YoutubePlaylist):
    def __init__(self, name, playlist_id=None, queue_id=None, backlog_id=None, backlog_source=None, **kwargs):
        super().__init__(name, 'primary', playlist_id, **kwargs)

        self.queue_id = queue_id
        self.backlog_id = backlog_id
        if self.queue_id is None and self.name in self.ranks.queues:
            self.queue_id = self.ranks.queues[self.name]
        if self.queue_id is None:
            raise ValueError("Invalid playlist '%s'; no queue playlist ID supplied" % self.name)

        if self.backlog_id is None and self.name in self.ranks.backlogs:
            self.backlog_id = self.ranks.backlogs[self.name]
        if self.backlog_id is None:
            raise ValueError("Invalid playlist '%s'; no backlog playlist ID supplied" % self.name)

        self.backlog = BacklogPlaylist(
            name="primary",
            parent_tier_name=name,
            backlog_source=backlog_source,
            **kwargs
        )

    def fetch_queue(self):
        self.queue = self.get_items(id=self.queue_id)

        return self.queue

    def get_video_duration(self, vid_data):
        duration = vid_data['vid_data']['contentDetails']['duration'].replace('P', '').replace('T', '')
        days = 0
        hours = 0
        minutes = 0
        seconds = 0
        if 'D' in duration:
            days_list = duration.split('D')
            hours = days * 24
            duration = days_list[1]
        if 'H' in duration:
            hours_list = duration.split('H')
            hours = hours + int(hours_list[0])
            minutes = hours * 60
            duration = hours_list[1]
        if 'M' in duration:
            minutes_list = duration.split('M')
            minutes = minutes + int(minutes_list[0])
            seconds = minutes * 60
            duration = minutes_list[1]
        if 'S' in duration:
            seconds_list = duration.split('S')
            seconds = seconds + int(seconds_list[0])

        return seconds

    def sort_playlist(self, import_queue=False):
        config = utilities.ConfigHandler()
        max_duration = config.variables['VIDEO_MAX_DURATION']['MINUTES']*60 + config.variables['VIDEO_MAX_DURATION']['HOURS']*3600
        playlist_max_length = self.config.variables['AUTOLIST_MAX_LENGTH']
        total = deepcopy(self.videos)
        total_sorted = self.sort(total)
        if len(total_sorted) > playlist_max_length:
            total_sorted = self.overflow_to_backlog(total_sorted, playlist_max_length)

        playlist_items_to_change = {}
        if import_queue:
            if len(self.queue) == 0:
                self.fetch_queue()
            total.update(deepcopy(self.queue))
            total_sorted = self.sort(total)

        for vid_id in sorted(total_sorted, key=lambda x: total_sorted[x]['playlist_data']['snippet']['position']):
            vid_data = total_sorted[vid_id]
            duration = self.get_video_duration(vid_data)
            if duration <= max_duration:
                new_pos = total_sorted[vid_id]['playlist_data']['snippet']['position']
                vid_data = self.videos[vid_id] if vid_id not in self.queue else self.queue[vid_id]
                title = vid_data['vid_data']['snippet']['title']
                if vid_id in self.queue:
                    vid_data = self.queue[vid_id]
                    vid_data['playlist_data']['snippet']['destinationPlaylistId'] = self.id
                    vid_data['playlist_data']['snippet']['position'] = new_pos
                    playlist_items_to_change[vid_id] = deepcopy(vid_data)
                    self.videos = deepcopy(self.modify_pos(deepcopy(self.videos), vid_id, title, new_pos, True))
                else:
                    old_pos = vid_data['playlist_data']['snippet']['position']
                    total_sorted[vid_id]['playlist_data']['snippet']['oldPosition'] = old_pos
                    if new_pos != old_pos:
                        playlist_items_to_change[vid_id] = deepcopy(total_sorted[vid_id])
                        self.videos = deepcopy(self.modify_pos(deepcopy(self.videos), vid_id, title, new_pos))

        for vid_id in sorted(playlist_items_to_change, key=lambda x: playlist_items_to_change[x]['playlist_data']['snippet']['position']):
            vid_data = playlist_items_to_change[vid_id]
            pos = vid_data['playlist_data']['snippet']['position']

            if 'destinationPlaylistId' in vid_data['playlist_data']['snippet']:
                self.transfer_playlist_item(vid_data=vid_data, vid_id=vid_id, old_playlist='queue', position=pos)
            else:
                self.update_playlist_item_position(vid_data=vid_data, vid_id=vid_id, position=pos)

        return total_sorted

    def get_backlog(self, num):
        self.backlog = self.backlog.sort_playlist()
        return None

    def populate_backlog(self):
        return None

    def overflow_to_backlog(self, total_sorted, max_length):
        trimmed_sorted = total_sorted
        overflow = {}
        for vid_id in sorted(total_sorted, key=lambda x: total_sorted[x]['playlist_data']['snippet']['position']):
            position = total_sorted[vid_id]['playlist_data']['snippet']['position']
            if position > max_length:
                overflow[vid_id] = deepcopy(total_sorted[vid_id])
            else:
                trimmed_sorted[vid_id] = deepcopy(total_sorted[vid_id])

        return trimmed_sorted


class BacklogPlaylist(YoutubePlaylist):
    def __init__(self, name, playlist_id=None, backlog_source=None, **kwargs):
        super().__init__(name, 'backlog', playlist_id, **kwargs)

        self.backlog_source_name = backlog_source
        if self.id is None and self.name in self.types['backlog']:
            self.id = self.types['backlog'][self.name]
        if self.id is None:
            raise ValueError("Invalid playlist '%s'; no backlog ID supplied" % self.name)

    def fetch_num_items(self, num):
        if self.backlog_source_name is not None:
            backlog_sorted_channels = self.get_ordered_channels(tier_name=self.backlog_source_name)
        parent_sorted_channels = self.get_ordered_channels(tier_name=self.name)
        return None


class QueuePlaylist(YoutubePlaylist):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tiers = {}
        self.ranks = ranks.RanksHandler()

    def sort(self):
        channels = {}
        for vid_data in self.videos:
            snippet = vid_data['snippet']
            if snippet['channelTitle'] not in channels:
                channels[snippet['channelTitle']] = []
            channels[snippet['channelTitle']].append(snippet)

        # for tier_data in self.ranks.ranks:
        #     tier = tier_data['tier']
        #     if tier not in self.tiers:
        #         self.tiers[tier] = []
        #     ordered_channel_ids = self.ranks.get_playlists_and_channels(tier)
        #     utilities.print_json(ordered_channel_ids)
        #     for tier in ordered_channel_ids:
        #         for channel_id in ordered_channel_ids[tier]:
        #             if channel_id in channels:
        #                 for snippet in channels[channel_id]:
        #                     self.tiers[tier].append("%s: %s" % (snippet['channelTitle'], snippet['title']))


class SortHandler:
    def __init__(self, **kwargs):
        config = utilities.ConfigHandler()
        self.ranks = ranks.RanksHandler()
        self.ranks.get_tiers()
        self.tier_names = kwargs['tiers']
        self.queue_id = self.ranks.playlists['queue']
        self.watch_later_id = self.ranks.playlists['watch_later']
        self.backlog_id = self.ranks.playlists['backlog']
        self.queue = QueuePlaylist(name='queue', id=self.queue_id)
        self.tier_playlist_ids = {}
        self.tier_playlists = {}

    def import_queue(self):
        self.queue.get_items()
        self.queue.sort()

    def get_all_tier_playlist_ids(self):
        counter = 0
        self.tier_playlist_ids = {}
        for tier in self.ranks.tiers:
            if tier.name in self.tier_names:
                if tier.name == 'primary':
                    if tier.playlist_id is None:
                        self.tier_playlist_ids[tier.name] = self.watch_later_id
                    else:
                        self.tier_playlist_ids[tier.name] = tier.playlist_id
                    counter += 1
                else:
                    counter = self.get_tier_playlists(tier, counter)

        return self.tier_playlist_ids

    def get_all_playlists(self):
        if len(self.tier_playlist_ids) == 0:
            self.get_all_tier_playlist_ids()

        self.tier_playlists = {}
        for tier_name in self.tier_playlist_ids:
            playlist_id = self.tier_playlist_ids[tier_name]
            self.tier_playlists[tier_name] = YoutubePlaylist(playlist_id=playlist_id)

        return self.tier_playlists

    def get_tier_playlists(self, tier, counter, parent_playlist_id=None):
        if tier.playlist_id is None:
            tier.playlist_id = parent_playlist_id
        self.tier_playlist_ids[tier.name] = tier.playlist_id
        counter += 1

        if len(tier.subtiers) > 0:
            for subtier in tier.subtiers:
                counter = self.get_tier_playlists(subtier, counter, tier.playlist_id)

        return counter