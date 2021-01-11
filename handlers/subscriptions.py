from handlers import playlist, utilities
from handlers.utilities import ConfigHandler
from handlers.client import YoutubeClientHandler
from copy import deepcopy
import json

class SubscriptionsHandler:
    def __init__(self, **kwargs):
        config = ConfigHandler()
        self.subscriptions = json.load(open(config.subscriptions_filepath, mode='r'))
        self.current = deepcopy(self.subscriptions)
        self.old = {}
        self.new = {}
        self.client = YoutubeClientHandler().client
        self.raw = []

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
            'details': {}
        }

        for item in self.raw:
            title = item['snippet']['title']
            id = item['snippet']['resourceId']['channelId']
            core = id[2:]
            uploads = 'UU' + id[2:]
            channels_output['details'][title] = {
                'title': title,
                'id': id,
                'uploads': uploads,
                'core': core
            }

        return channels_output

    def update_subscriptions(self):
        raw = self.fetch_subs()
        processed = self.process_raw_subs_data()
        delta = self.compare_details(self.current['details'], processed['details'])

        renamed = self.check_for_renames(
            old=self.current['details'],
            new=processed['details']
        )

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