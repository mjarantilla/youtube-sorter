from handlers import client, playlist, utilities
from datetime import datetime
from copy import deepcopy
import json, os

logger = utilities.Logger()


class Tier:
    def __init__(self, **kwargs):
        self.name = kwargs['tier']
        self.subtiers = []
        self.channels = kwargs['channels'] if 'channels' in kwargs else []
        self.channel_data = []
        self.separate = kwargs['separate'] if 'separate' in kwargs and kwargs['separate'] else False
        self.playlist_id = kwargs['playlist_id'] if 'playlist_id' in kwargs else None
        self.videos = []
        if 'subtiers' in kwargs:
            self.get_subtiers(**kwargs)
        self.get_channel_data()
        self.json = {}

    def get_subtiers(self, **kwargs):
        self.subtiers = []
        subtiers = kwargs['subtiers']
        counter = 0
        for subtier_kwargs in subtiers:
            if 'tier' not in subtier_kwargs:
                subtier_kwargs['tier'] = "%s_%s" % (self.name, str(counter).zfill(2))
                counter += 1
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
            if channel_name in subscriptions:
                self.channel_data.append(subscriptions[channel_name])

    def get_channels(self):
        channels = self.channels
        for subtier in self.subtiers:
            channels = channels + subtier.get_channels()

        self.channel_data = channels

        return channels

    def print_rank(self):
        return None

    def update_channels(self, changes):
        logger.write("Updating {0} channels".format(self.name))
        self.rename_channels(changes['renamed'])
        self.remove_channels(changes['removed'])

    def remove_channels(self, removed):
        new_set = []
        for channel in self.channels:
            if channel not in removed:
                new_set.append(channel)
            else:
                logger.write("Removing {0} from {1}".format(channel, self.name))

        self.channels = new_set
        for subtier in self.subtiers:
            subtier.remove_channels(removed)

    def rename_channels(self, renamed):
        new_set = []
        renamed_titles = {}
        for title_pair in renamed:
            renamed_titles[title_pair['old']] = title_pair['new']

        for channel in self.channels:
            if channel not in renamed_titles:
                new_set.append(channel)
            else:
                logger.write("Renaming {0} to {1} in {2}".format(channel, renamed_titles[channel], self.name))
                new_set.append(renamed_titles[channel])

        self.channels = new_set

        for subtier in self.subtiers:
            subtier.rename_channels(renamed)

        return None

    def return_json(self):
        self.json = {
            'tier': self.name,
            'channels': []
        }

        for channel in self.channels:
            self.json['channels'].append(channel)

        if len(self.subtiers) > 0:
            self.json['subtiers'] = []
        for subtier in self.subtiers:
            subtier_json = subtier.return_json()
            self.json['subtiers'].append(subtier_json)

        if self.playlist_id is not None:
            self.json['playlist_id'] = self.playlist_id

        return self.json


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
        self.queues = self.data['queues']
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

    def update_channels(self, changes):
        for tier in self.rank_data:
            tier.update_channels(changes)

        self.data['added'] = changes['added']

    def get_json(self):
        new_ranks_json = []
        for tier in self.rank_data:
            new_ranks_json.append(tier.return_json())

        self.data['ranks'] = deepcopy(new_ranks_json)
        return new_ranks_json

    def write(self):
        config = utilities.ConfigHandler()
        filepath = config.ranks_filepath
        date_format = config.variables['LOG_DATE_FORMAT']
        log_date = datetime.now()
        backup_suffix = log_date.strftime(date_format)

        # Backup subscription file
        backup_ranks_file = "{0}.{1}".format(filepath, backup_suffix)
        os.rename(src=filepath, dst=backup_ranks_file)

        # Write new subscription file
        fp = open(filepath, mode='w')
        utilities.print_json(self.data, fp=fp)


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
