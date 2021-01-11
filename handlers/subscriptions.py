from handlers import playlist, utilities
from handlers.utilities import ConfigHandler
from handlers.client import YoutubeClientHandler
from handlers.ranks import RanksHandler
from copy import deepcopy
from datetime import datetime
import json
import os

class SubscriptionsHandler:
    def __init__(self, **kwargs):
        self.config = ConfigHandler()
        self.subscriptions = json.load(open(self.config.subscriptions_filepath, mode='r'))
        self.current = deepcopy(self.subscriptions)
        self.old = {}
        self.client = YoutubeClientHandler().client
        self.raw = []
        self.changes = {}

    def fetch_subs(self):
        kwargs = {
            'part': 'snippet',
            'channelId': 'UCWW8SlHj1Ax0iGE3uJGnNrw',
            'maxResults': 50,
            'order': 'alphabetical'
        }

        response = {'nextPageToken': None}
        results = []
        page_tokens = []
        titles = {}
        page = 0
        while 'nextPageToken' in response:
            titles[page] = []
            request = self.client.subscriptions().list(**kwargs)
            response = request.execute()
            for item in response['items']:
                results.append(item)
            if 'nextPageToken' in response:
                kwargs['pageToken'] = response['nextPageToken']
                page_tokens.append(response['nextPageToken'])
            page += 1

        self.raw = results

        return self.raw

    def process_raw_subs_data(self):
        channels_output = {
            'details': {},
            'titles': [],
            'changes': {},
            'unsubscribed': []
        }

        filtered_channels = RanksHandler().filtered_channels

        if 'changes' in self.current:
            channels_output['changes'] = deepcopy(self.current['changes'])
        if 'unsubscribed' in self.current:
            channels_output['unsubscribed'] = deepcopy(self.current['unsubscribed'])

        for item in self.raw:
            title = item['snippet']['title']
            id = item['snippet']['resourceId']['channelId']
            core = id[2:]
            uploads = 'UU' + id[2:]
            if id not in filtered_channels:
                channels_output['details'][title] = {
                    'title': title,
                    'id': id,
                    'uploads': uploads,
                    'core': core
                }

        for title in channels_output['details']:
            channels_output['titles'].append(title)

        return channels_output

    def update_subscriptions(self):
        delta = {}
        raw = self.fetch_subs()
        processed = self.process_raw_subs_data()
        delta = self.compare_details(self.current['details'], processed['details'])

        renamed_data = self.check_for_renames(
            old=self.current['details'],
            new=processed['details']
        )
        old_names = {}
        for title in renamed_data:
            item = renamed_data[title]
            for old_name in item['previous_names']:
                old_names[old_name] = title

        removed = []
        renamed = []
        added = []
        for title in delta['in_a']:
            if title in old_names.keys():
                renamed.append(
                    {
                        'old': title,
                        'new': old_names[title]
                    }
                )
            else:
                removed.append(title)

        for title in delta['in_b']:
            if title not in renamed_data.keys():
                added.append(title)

        date_format = self.config.variables['EVENT_LOG_FORMAT']
        log_date = datetime.now()
        datetimestamp = log_date.strftime(date_format)
        self.changes = {
            'removed': removed,
            'renamed': renamed,
            'added': added
        }
        processed['changes'][datetimestamp] = self.changes
        for channel_name in removed:
            processed['unsubscribed'].append(channel_name)

        self.old = deepcopy(self.current)
        self.current = processed

    def update_files(self):
        backup_suffix = self.config.variables['LOG_DATE_FORMAT']
        ranks_file = self.config.ranks_filepath
        subs_file = self.config.subscriptions_filepath
        subs_fp = open(subs_file, mode='w')

        backup_subs_file = "{0}.{1}".format(self.config.subscriptions_filepath, backup_suffix)
        os.rename(src=subs_file, dst=backup_subs_file)
        utilities.print_json(self.current, fp=subs_fp)

    def compare_details(self, details_a, details_b):
        delta = {
            'in_a': [],
            'in_b': [],
            'in_both': []
        }

        for title in details_a:
            if title in details_b:
                delta['in_both'].append(title)
            else:
                delta['in_a'].append(title)

        for title in details_b:
            if title not in details_a:
                delta['in_b'].append(title)

        return delta

    def check_for_renames(self, **kwargs):
        old = kwargs['old']
        new = kwargs['new']
        renamed = {}

        set_a_ids = {}

        for item in old:
            id = old[item]['id']
            set_a_ids[id] = item

        for item in new:
            id = new[item]['id']
            if id in set_a_ids:
                if set_a_ids[id] != item:
                    renamed[item] = deepcopy(new[item])
                    if 'previous_names' not in renamed[item]:
                        renamed[item]['previous_names'] = [set_a_ids[id]]

        return renamed