from handlers import client, playlist
import json
from handlers import utilities


class Tier:
    def __init__(self, **kwargs):
        self.name = kwargs['tier']
        self.subtiers = []
        self.channels = kwargs['channels'] if 'channels' in kwargs else []
        self.channel_data = []
        self.separate = kwargs['separate'] if 'separate' in kwargs and kwargs['separate'] else False
        self.playlist = kwargs['playlist'] if 'playlist' in kwargs else None
        self.videos = []
        if 'subtiers' in kwargs:
            self.get_subtiers(**kwargs)
        self.get_channel_data()

    def get_subtiers(self, **kwargs):
        self.subtiers = []
        subtiers = kwargs['subtiers']
        for subtier_kwargs in subtiers:
            if 'separate' not in subtier_kwargs:
                subtier_kwargs['separate'] = self.separate
            if 'playlist' not in subtier_kwargs and self.playlist is not None:
                subtier_kwargs['playlist'] = self.playlist
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
        config = utilities.ConfigHandler()
        self.data = json.load(open(config.ranks_filepath, mode='r'))
        self.ranks = self.data['ranks']
        self.filtered = self.data['filters']
        self.filtered_channels = []
        for channel_name in self.filtered['channels']:
            self.filtered_channels.append(self.filtered['channels'][channel_name])
        self.playlists = self.data['playlist_ids']
        for tier in config.variables['TIER_PLAYLISTS']:
            self.playlists[tier] = config.variables['TIER_PLAYLISTS'][tier]
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
