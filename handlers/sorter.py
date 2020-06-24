from handlers import client, utilities, ranks
import threading


class YoutubePlaylist(threading.Thread):
    def __init__(self, **kwargs):
        # Expected kwargs:
        # - name
        # - id (optional)

        super().__init__()
        self.ranks = ranks.RanksHandler()
        self.client = client.YoutubeClientHandler().get_client()
        self.name = kwargs['name']

        # Sets playlist ID to what is submitted as a kwarg.
        # If no ID is set in kwarg, look up playlist ID by name in ranks.json.
        # If no ID is present in ranks.json, throw an error.
        self.id = kwargs['id'] if 'id' in kwargs else None
        if self.id is None and self.name in self.ranks.playlists:
            self.id = self.ranks.playlists[self.name]
        if self.id is None:
            raise ValueError("Invalid playlist; no playlist ID supplied")

        # Resources to use internally
        self.ordered_channels = []
        self.videos = []
        self.new_items_queue = []
        self.deleted_items_queue = []
        self.backlog = []

    def get_items(self):
        kwargs = {
            'playlistId': self.id,
            'maxResults': 50,
            'part': "contentDetails"
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
        for item in items:
            vid_ids.append(item['contentDetails']['videoId'])

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

        self.videos = items

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
        channels = []
        for tier in handler.ranks:
            channels += add_subtier_channels(
                playlist_name=self.name,
                tier_data=tier
            )

        return channels

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