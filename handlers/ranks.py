from handlers import client
import json
from handlers import utilities

class Tier:
    def __init__(self, **kwargs):
        self.name = kwargs['tier']
        self.subtiers = None
        self.get_subtiers()
        self.channels = kwargs['channels'] if 'channels' in kwargs else []
        self.channel_upload_playlists = []
        self.get_channel_ids()
        self.separate = kwargs['separate'] if 'separate' in kwargs and kwargs['separate'] else False
        self.playlist_id = kwargs['playlist_id'] if 'playlist_id' in kwargs else None
        self.videos = []

    def get_subtiers(self, **kwargs):
        self.subtiers = []
        subtiers = kwargs['subtiers']
        for subtier_kwargs in subtiers:
            if 'playlist_id' not in subtier_kwargs and self.playlist_id is not None:
                subtier_kwargs['playlist_id'] = self.playlist_id
            self.subtiers.append(Tier(**subtier_kwargs))

    def assemble_video_list(self):
        full_list = self.videos

        for subtier in self.subtiers:
            subtier.assemble_video_list()
            full_list = full_list + subtier.videos

    def get_channel_ids(self):
        self.channel_upload_playlists = []
        config = utilities.ConfigHandler()
        subscriptions = json.load(open(config.subscriptions_filepath, mode='r'))

        for channel_name in self.channels:
            self.channel_upload_playlists.append(subscriptions[channel_name]['uploads'])

    def get_videos(self):
        self.videos = []
        youtube = client.YoutubeClientHandler()

    def print_rank(self):
        return None

class Autolister:
    def __init__(self):
        self.config = utilities.ConfigHandler()
        ranks_dictionary = json.load(open(self.config.ranks_filepath, mode='r'))
        self.max_length = self.config
        self.ranks = ranks_dictionary['ranks']
        self.filtered_channels = ranks_dictionary['filters']['channels']
        self.filtered_video_titles = ranks_dictionary['filters']['videos']

    def define_ranks(self):
        for rank_block in self.ranks:
