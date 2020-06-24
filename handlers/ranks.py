from handlers import client, queue
import json
import threading
from handlers import utilities


class Tier:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = kwargs['tier']
        self.subtiers = []
        self.channels = kwargs['channels'] if 'channels' in kwargs else []
        self.channel_data = []
        self.separate = kwargs['separate'] if 'separate' in kwargs and kwargs['separate'] else False
        self.playlist_id = kwargs['playlist_id'] if 'playlist_id' in kwargs else None
        if self.playlist_id == "":
            self.playlist_id = None
        self.backlog_id = kwargs['backlog_id'] if 'backlog_id' in kwargs else None
        if self.backlog_id == "":
            self.backlog_id = None
        self.videos = []
        if 'subtiers' in kwargs:
            self.get_subtiers(**kwargs)
        self.get_channel_data()

    def get_subtiers(self, **kwargs):
        if len(kwargs) == 0:
            kwargs = self.kwargs
        self.subtiers = []
        subtiers = kwargs['subtiers']
        count = 0
        for subtier_kwargs in subtiers:
            if 'tier' not in subtier_kwargs:
                count += 1
                subtier_kwargs['tier'] = "%s_%s" % (self.name, str(count).zfill(2))
            if 'separate' not in subtier_kwargs:
                subtier_kwargs['separate'] = self.separate
            if 'playlist' not in subtier_kwargs and self.playlist_id is not None:
                subtier_kwargs['playlist'] = self.playlist_id
            self.subtiers.append(Tier(**subtier_kwargs))

    def assemble_video_list(self):
        full_list = self.videos

        for subtier in self.subtiers:
            subtier.assemble_video_list()
            full_list = full_list + subtier.videos

    def get_channel_data(self):
        self.channel_data = []
        config = utilities.ConfigHandler()
        subscriptions = json.load(open(config.subscriptions_filepath, mode='r'))['details']

        for channel_name in self.channels:
            self.channel_data.append(subscriptions[channel_name])

    def get_channels(self):
        channels = self.channels
        for subtier in self.subtiers:
            channels = channels + subtier.get_channels()

        self.channel_data = channels

        return channels

    def print_rank(self):
        return None


class RanksHandler():
    def __init__(self):
        self.config = utilities.ConfigHandler()
        self.data = json.load(open(self.config.ranks_filepath, mode='r'))
        self.ranks = self.data['ranks']
        self.tiers = []
        self.filtered = self.data['filters']
        self.filtered_channels = []
        for channel_name in self.filtered['channels']:
            self.filtered_channels.append(self.filtered['channels'][channel_name])
        self.playlists = self.data['playlist_ids']
        for tier in self.config.variables['TIER_PLAYLISTS']:
            self.playlists[tier] = self.config.variables['TIER_PLAYLISTS'][tier]
        self.rank_data = []

    def define_ranks(self):
        for rank_block in self.ranks:
            if 'playlist' not in rank_block:
                rank_block['playlist'] = 'watch_later'
            rank = Tier(**rank_block)
            self.rank_data.append(rank)

        return self.rank_data

    def channel_filtered(self, channel_id):
        if channel_id in self.filtered_channels:
            return True
        else:
            return False

    def get_playlists_and_channels(self, tier):
        def get_tier_channels(data, channels, parent_playlist=None):
            if 'channels' in data:
                if 'playlist_id' in data or parent_playlist is None:
                    if data['playlist_id'] not in channels:
                        channels[data['playlist_id']] = []
                    channels[data['playlist_id']] += data['channels']
                else:
                    if parent_playlist not in channels:
                        channels[parent_playlist] = []
                    channels[parent_playlist] += data['channels']

            if 'subtiers' in data:
                counter = 0
                for subtier_data in data['subtiers']:
                    if 'tier' not in subtier_data:
                        counter += 1
                        subtier_data['tier'] = "%s_%s" % (data['tier'], str(counter).zfill(2)  )
                    channels = get_tier_channels(subtier_data, channels, parent_playlist)
            return channels

        tier_data = None
        for tier_data in self.ranks:
            if tier_data["tier"] == tier:
                break
            tier_data = None

        if tier_data is not None:
            if tier_data["tier"] == tier:
                channels = {}
                if 'playlist_id' in tier_data:
                    playlist = tier_data['playlist_id']
                else:
                    playlist = "PL8wvcc8NSIHKg8C1O39efqI4KSNwivMAw"
                results = get_tier_channels(
                    data=tier_data,
                    channels=channels,
                    parent_playlist=playlist
                )

                subscriptions = json.load(open(self.config.subscriptions_filepath, mode='r'))['details']
                # id_list = []
                # for result in results:
                #     # id_list.append(subscriptions[result]['id'])
                #     id_list.append(result)  # Indexing by channel title rather than channel ID
                #
                # return id_list
                return results
        return []


    def get_tiers(self):
        for tier_data in self.ranks:
            self.tiers.append(Tier(**tier_data))


class Autolister:
    def __init__(self):
        self.config = utilities.ConfigHandler()
        ranks_dictionary = json.load(open(self.config.ranks_filepath, mode='r'))
        self.max_length = self.config
        self.ranks = ranks_dictionary['ranks']
        self.filtered_channels = ranks_dictionary['filters']['channels']
        self.filtered_video_titles = ranks_dictionary['filters']['videos']

    # def define_ranks(self):
    #     for rank_block in self.ranks:
