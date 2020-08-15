from handlers import client, utilities, ranks
from copy import deepcopy
import threading


class YoutubePlaylist(threading.Thread):
    def __init__(self, name, id=None, queue_id=None, **kwargs):
        # Expected kwargs:
        # - name
        # - id (optional)

        super().__init__()
        self.ranks = ranks.RanksHandler()
        self.client = client.YoutubeClientHandler().get_client()
        self.name = name

        # Sets playlist ID to what is submitted as a kwarg.
        # If no ID is set in kwarg, look up playlist ID by name in ranks.json.
        # If no ID is present in ranks.json, throw an error.
        self.id = id
        self.queue_id = queue_id
        if self.id is None and self.name in self.ranks.playlists:
            self.id = self.ranks.playlists[self.name]
        if self.id is None:
            raise ValueError("Invalid playlist '%s'; no playlist ID supplied" % self.name)

        if self.queue_id is None and self.name in self.ranks.queues:
            self.queue_id = self.ranks.queues[self.name]
        if self.queue_id is None:
            raise ValueError("Invalid playlist '%s'; no queue playlist ID supplied" % self.name)

        # Resources to use internally
        self.ordered_channels = []
        self.videos = []
        self.queue = []
        self.deleted_items_queue = []
        self.backlog = []
        self.test = kwargs['test']

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
            "part": "snippet",
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

    def get_ordered_channels(self):
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
                playlist_name=self.name,
                tier_data=tier
            )
        channels = []
        for channel_name in channel_names:
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

    def fetch_queue(self):
        self.queue = self.get_items(id=self.queue_id)

        return self.queue

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

    def sort_playlist(self, import_queue=False):
        total = deepcopy(self.videos)
        total_sorted = self.sort(total)
        playlist_items_to_change = {}
        if import_queue:
            if len(self.queue) == 0:
                self.fetch_queue()
            total.update(deepcopy(self.queue))
            total_sorted = self.sort(total)

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

        for vid_id in sorted(total_sorted, key=lambda x: total_sorted[x]['playlist_data']['snippet']['position']):
            vid_data = total_sorted[vid_id]
            channel = vid_data['vid_data']['snippet']['channelTitle']
            title = vid_data['vid_data']['snippet']['title']
            position = vid_data['playlist_data']['snippet']['position']
            print("%i) %s: %s" % (position, channel, title))

        for vid_id in sorted(playlist_items_to_change, key=lambda x: playlist_items_to_change[x]['playlist_data']['snippet']['position']):
            vid_data = playlist_items_to_change[vid_id]
            pos = vid_data['playlist_data']['snippet']['position']

            if 'destinationPlaylistId' in vid_data['playlist_data']['snippet']:
                self.transfer_playlist_item(vid_data=vid_data, vid_id=vid_id, old_playlist='queue', position=pos)
            else:
                self.update_playlist_item_position(vid_data=vid_data, vid_id=vid_id, position=pos)

        return total_sorted

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
        else:
            print("Would have executed, but currently in test mode")

    def delete_playlist_item(self):
        return None

    def run(self):
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
            self.tier_playlists[tier_name] = YoutubePlaylist(id=playlist_id)

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