from datetime import datetime, timedelta
import os
import json

ERROR_CODES = [403, 404, 408, 500, 502, 503, 504]


def update_global_vars(initialize=False):

    global config_file
    global config
    global SCOPES
    global API_SERVICE_NAME
    global API_VERSION
    global YOUTUBE_DATE_FORMAT
    global DATE_FORMAT
    global DAYS_TO_SEARCH
    global CURRENT_DATE
    global HOME_DIR
    global LOG_DIR
    global LOG_FILE
    global CLIENT_SECRETS_FILE
    global RECORDS_FILE
    global RANKS_FILE
    global SUBSCRIPTIONS_FILE
    global PRIVATE_VIDEOS_FILE
    global LOG_DATE_FORMAT
    global LAST_TIER
    global OMITTED_CHANNELS
    global OMITTED_VID_SERIES
    global VIDEOS
    global AUTOLIST_MAX_LENGTH
    global WATCH_LATER_ID
    global BACKLOG_ID
    global F1_PLAYLIST_ID
    global QUEUE_ID
    global SECONDARY_ID
    global AUTOLIST_ITEMS
    global TITLES
    global VIDEO_MAX_DURATION_HOURS
    global VIDEO_MAX_DURATION_MINUTES
    global ranks
    global filters
    global filtered_channels
    global XL_ID
    global TEST
    global TIER_PLAYLISTS
    global FILLER_LENGTH
    global FILLER_INDEX

    config_file = 'config.json'
    config_fp = open(config_file)
    config = json.load(config_fp)


    SCOPES = config['SCOPES']
    API_SERVICE_NAME = config['API_SERVICE_NAME']
    API_VERSION = config['API_VERSION']
    YOUTUBE_DATE_FORMAT = config['YOUTUBE_DATE_FORMAT']
    LOG_DATE_FORMAT = config['LOG_DATE_FORMAT']
    DATE_FORMAT = config['DATE_FORMAT']
    DAYS_TO_SEARCH = config['DAYS_TO_SEARCH']
    CURRENT_DATE = datetime.now().strftime(DATE_FORMAT)

    HOME_DIR = os.getcwd()
    LOG_DIR = '/'.join([HOME_DIR, 'logs'])
    CLIENT_SECRETS_FILE = '/'.join([HOME_DIR, config['CLIENT_SECRETS_FILE']])
    RECORDS_FILE = '/'.join([HOME_DIR, config['RECORDS_FILE']])
    RANKS_FILE = '/'.join([HOME_DIR, config['RANKS_FILE']])
    SUBSCRIPTIONS_FILE = '/'.join([HOME_DIR, config['SUBSCRIPTIONS_FILE']])
    PRIVATE_VIDEOS_FILE = '/'.join([HOME_DIR, config['PRIVATE_VIDEOS_FILE']])
    LOG_FILE = '/'.join([LOG_DIR, 'current.log'])
    if initialize:
        if os.path.isfile(LOG_FILE):
            print("Renaming log file")
            os.rename(LOG_FILE, LOG_FILE + "." + datetime.now().strftime(LOG_DATE_FORMAT))
        else:
            log("Creating new log file")
            open(LOG_FILE, mode='w')
    LAST_TIER = config['LAST_TIER']

    ranks_fp = open(RANKS_FILE)
    ranks = json.load(ranks_fp)
    filters = ranks['filters']
    ranks_fp.close()
    if type == 'channels':
        filtered_channels = []
        for channel in filters['channels']:
            filtered_channels.append(filters['channels'][channel])
    OMITTED_CHANNELS = []
    for channel in filters['channels']:
        OMITTED_CHANNELS.append(filters['channels'][channel])
    OMITTED_VID_SERIES = filters['videos']

    VIDEOS = []
    AUTOLIST_MAX_LENGTH = config['AUTOLIST_MAX_LENGTH']
    WATCH_LATER_ID = config['WATCH_LATER_ID']
    XL_ID = config['XL_WATCH_LATER_ID']
    BACKLOG_ID = config['BACKLOG_ID']
    F1_PLAYLIST_ID = config['F1_PLAYLIST_ID']
    QUEUE_ID = config['QUEUE_ID']
    SECONDARY_ID = config['SECONDARY_ID']
    AUTOLIST_ITEMS = []
    TITLES = []
    VIDEO_MAX_DURATION_MINUTES = config['VIDEO_MAX_DURATION']['MINUTES']
    VIDEO_MAX_DURATION_HOURS = config['VIDEO_MAX_DURATION']['HOURS']
    TEST = config['TEST_MODE']
    TIER_PLAYLISTS = config['TIER_PLAYLISTS']
    FILLER_LENGTH = config['FILLER_LENGTH']
    FILLER_INDEX = config['FILLER_INDEX']


def log(msg, silent=False):
    try:
        log_date = datetime.now()
        log_date_formatted = log_date.strftime(YOUTUBE_DATE_FORMAT)
        # renamed = False
        # if log_date.hour == 0 and log_date.minute == 0 and log_date.second == 0:
        #     print("Renaming log file")
        #     update_global_vars(initialize=True)
        #     log_msg = ': '.join(
        #         [
        #             str(log_date_formatted),
        #             "Renaming log file"
        #         ]
        #     )
        #     shutil.copyfile(LOG_FILE, LOG_FILE + "." + datetime.now().strftime(LOG_DATE_FORMAT))
        #     renamed = True
        #
        # if renamed:
        #     log_fp = open(LOG_FILE, mode='w')
        #     print("Renamed log file", file=log_fp)
        # else:
        log_fp = open(LOG_FILE, mode='a')
        log_msg = ': '.join(
            [
                str(log_date_formatted),
                msg
            ]
        )

        print(log_msg, file=log_fp)
        if not silent:
            print(log_msg)
        log_fp.close()
    except:
        print_json(msg)
        raise


def print_json(obj, fp=None):
    import json

    if fp is None:
        print(json.dumps(obj, separators=(',', ': '), indent=2, sort_keys=True))
    else:
        print(json.dumps(obj, separators=(',', ': '), indent=2, sort_keys=True), file=fp)


def get_client(pickle='sorter.pickle'):
    from handlers.client import YoutubeClientHandler

    handler = YoutubeClientHandler(pickle=pickle)
    client = handler.client

    return client


def merge_sort_split_v2(
        sort_current=True,
        sort_f1=True,
        import_queue=True,
        sort_secondary=True,
        sort_xl=True,
        sort=True
    ):
    update_global_vars()
    log("Starting sort")
    if sort:
        sort_current = True
        sort_secondary = True
        sort_f1 = True
        sort_xl = True
        import_queue = True

    if sort_current and sort_xl and sort_secondary and sort_f1 and import_queue:
        log("Sorting all titles")
    else:
        if sort_current:
            log("Sorting primary autolist")
        if sort_xl:
            log("Sorting XL videos")
        if sort_secondary:
            log("Sorting secondary videos")
        if sort_f1:
            log("Sorting F1 videos")
        if import_queue:
            log("Importing queue")

    # Load data about videos marked "private" on YouTube
    private_fp = open(PRIVATE_VIDEOS_FILE, mode='r')
    private_vids_data = json.load(private_fp)
    private_videos = private_vids_data['private_videos']
    private_fp.close()
    private_fp = open(PRIVATE_VIDEOS_FILE, mode='w')
    json.dump({'private_videos': private_videos}, fp=private_fp, separators=(',', ': '), indent=2, sort_keys=True)
    private_fp.close()

    client = get_client()

    # Load channel priority rankings
    rankings_fp = open(RANKS_FILE)
    rankings = json.load(rankings_fp)

    # Load list of channel subscriptions
    subscriptions_fp = open(SUBSCRIPTIONS_FILE)
    subscriptions = json.load(subscriptions_fp)

    # Create channel index
    channel_index = {}
    subscriptions_details = subscriptions['details']
    for channel_title in subscriptions_details:
        channel_info = subscriptions_details[channel_title]
        channel_id = channel_info['id']
        channel_uploads = channel_info['uploads']
        channel_index[channel_id] = channel_title
    # for channel_title in rankings['ids']:
    #     channel_index[rankings['ids'][channel_title]] = channel_title

    # Fetch playlist
    top_index = 'tiers'
    tiers = rankings[top_index]
    ids = subscriptions['details']

    log("Combining playlists")

    combined = []

    if import_queue:
        current_queue = get_playlist_items(client, autolist_id=QUEUE_ID, playlist_title='queue')
        combined = combined + current_queue
    if sort_current:
        current_autolist = get_playlist_items(client, autolist_id=WATCH_LATER_ID, playlist_title='autolist')
        current_backlog = get_playlist_items(client, autolist_id=BACKLOG_ID, playlist_title='backlog')
        combined = combined + current_autolist + current_backlog
    if sort_f1:
        current_f1playlist = get_playlist_items(client, autolist_id=F1_PLAYLIST_ID, playlist_title='F1 playlist')
        combined = combined + current_f1playlist
    if sort_secondary:
        current_secondary = []
        for tier in TIER_PLAYLISTS:
            current_secondary = current_secondary + get_playlist_items(client, autolist_id=TIER_PLAYLISTS[tier],
                                                                       playlist_title="%s secondary playlist" % tier)
        log("Total secondary items: %s" % len(current_secondary))
        combined = combined + current_secondary
    if sort_xl:
        current_xl = get_playlist_items(client, autolist_id=XL_ID, playlist_title='xl playlist')
        combined = combined + current_xl

    # max_length = AUTOLIST_MAX_LENGTH + len(current_xl)
    # combine_f1 = True if len(combined) < max_length else False
    combine_f1 = False

    autolist = {}
    secondary_autolist = {}
    xl_autolist = {}
    f1_autolist = {}
    videos = []
    channel_ids = {}
    f1_channel_ids = []
    secondary_channel_ids = []
    already_added_ids = []

    log("Sorting channels")
    for tier in tiers:
        channel_ids[tier] = []
        if tier == '1':
            autolist[tier] = {}
            xl_autolist[tier] = {}
            log("Sorting top channels")
            top_channels = tiers['1']
            for category in sorted(top_channels):
                log(category)
                category_channels = top_channels[category]
                target = channel_ids[tier]
                if category == 'B: Formula One' and not combine_f1:
                    target = f1_channel_ids
                for channel in category_channels:
                    target.append(ids[channel]['id'])
                    autolist[tier][ids[channel]['id']] = []
                    xl_autolist[tier][ids[channel]['id']] = []
        else:
            autolist[tier] = []
            xl_autolist[tier] = []
            secondary_autolist[tier] = []
            for channel in tiers[tier]:
                if channel in ids:
                    channel_ids[tier].append(ids[channel]['id'])

    # Fetching data on all videos in combined list
    log("Getting detailed info on each video")
    for vid in combined:
        vid_id = vid['contentDetails']['videoId']
        request = client.videos().list(
            part='snippet,contentDetails',
            id=vid_id
        )
        response = execute(request)
        video = response['items'][0] if len(response['items']) > 0 else None
        try:
            duration = video['contentDetails']['duration'].replace('P', '').replace('T', '')
        except:
            print_json(video)
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
        if video is not None:
            vid_details = {
                'channelId': video['snippet']['channelId'],
                'channelTitle': video['snippet']['channelTitle'],
                'videoId': vid['contentDetails']['videoId'],
                'videoTitle': video['snippet']['title'],
                'publishedDate': video['snippet']['publishedAt'],
                'sourcePlaylistId': vid['snippet']['playlistId'],
                'playlistItemId': vid['id'],
                'position': vid['snippet']['position'],
                'duration': {
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds
                }
            }
            videos.append(vid_details)
        else:
            private_videos.append(vid_id)
            already_added_ids.append(vid_id)

    log("Adding private videos to private videos file")
    # Add any "private videos" to private videos file
    private_fp = open(PRIVATE_VIDEOS_FILE, mode='w')
    json.dump({'private_videos': private_videos}, fp=private_fp, separators=(',', ': '), indent=2, sort_keys=True)
    private_fp.close()

    log("Sorting top channel videos separately")
    # Sort Top Channel videos separately from regular channel videos
    for vid_details in sorted(videos, key=lambda x: x['publishedDate'], reverse=False):
        if vid_details['sourcePlaylistId'] == QUEUE_ID:
            # if vid_details['duration']['hours'] > 0:
            #     log("\tSkipping: %s" % vid_details['videoTitle'])
            #     continue
            # elif vid_details['duration']['minutes'] > VIDEO_MAX_DURATION_MINUTES:
            if vid_details['duration']['hours'] > 0:
                log("\tAdding: %s to XL List" % vid_details['videoTitle'])
            else:
                log("\tAdding: %s" % vid_details['videoTitle'])
        channel_id = vid_details['channelId']
        details = vid_details
        if channel_id in f1_channel_ids:
            if combine_f1:
                log("\tWatch Later: %s - %s" % (channel_index[channel_id], details['videoTitle']))
                autolist['1'][channel_id].append(details)
            else:
                log("\tF1: %s - %s" % (channel_index[channel_id], details['videoTitle']))
                if channel_id not in f1_autolist:
                    f1_autolist[channel_id] = []
                f1_autolist[channel_id].append(vid_details)
        else:
            for tier in autolist:
                if channel_id in channel_ids[tier]:
                    log("\tWatch Later: %s - %s" % (channel_index[channel_id], details['videoTitle']))
                    # if vid_details['duration']['minutes'] > VIDEO_MAX_DURATION_MINUTES \
                    if vid_details['duration']['hours'] > 0 and vid_details['sourcePlaylistId'] in [QUEUE_ID,
                                                                                                    XL_ID] and tier == '1':
                        target_list = xl_autolist
                    else:
                        target_list = autolist

                    if tier == '1':
                        target_list = target_list[tier][channel_id]
                    else:
                        target_list = target_list[tier]

                    target_list.append(details)

    log("Sorting F1 playlist")
    combined_f1playlist = []
    for channel_id in f1_channel_ids:
        if channel_id in f1_autolist:
            for vid_details in f1_autolist[channel_id]:
                combined_f1playlist.append(vid_details)

    new_f1_playlist = combined_f1playlist[:AUTOLIST_MAX_LENGTH]
    new_f1_backlog_length = len(combined_f1playlist) - AUTOLIST_MAX_LENGTH
    if new_f1_backlog_length > 0:
        new_f1_backlog = combined_f1playlist[-new_f1_backlog_length:]
    else:
        new_f1_backlog = []

    if len(new_f1_backlog) > 0:
        log("Creating new order for F1 backlog")
        for item in new_f1_backlog:
            vid_title = item['videoTitle']
            channel_title = item['channelTitle']
            label = ": ".join([channel_title, vid_title])
            log("\t" + label)

    log("Creating new order for autolist")
    # Add Top Channel videos to new autolist first
    new_combined = []
    xl_combined = []
    secondary_combined = []
    secondary_playlists = {}
    filler_playlist = []
    filler_count = FILLER_LENGTH
    filler_ids_added = []

    for tier in autolist:
        log("Creating Tier %s playlist" % tier)
        if tier == '1':
            for id in autolist[tier]:
                for vid_details in autolist[tier][id]:
                    new_combined.append(vid_details)
        else:
            for vid_details in autolist[tier]:
                filler_playlist.append(vid_details)

    max_filler_length = AUTOLIST_MAX_LENGTH * 2
    filler_playlist = filler_playlist[:max_filler_length]

    log("Checking max length")
    if len(new_combined) > AUTOLIST_MAX_LENGTH:
        new_autolist = new_combined[:AUTOLIST_MAX_LENGTH]
        new_backlog = new_combined[AUTOLIST_MAX_LENGTH:] + new_f1_backlog
        if len(new_backlog) < max_filler_length:
            fillers_to_add = max_filler_length - len(new_backlog)
            new_backlog = new_backlog + filler_playlist[:fillers_to_add]
    else:
        min_secondaries_to_add = 10
        secondaries_to_add = AUTOLIST_MAX_LENGTH - len(new_combined)
        log("Combined length: %i" % len(new_combined))
        log("Total secondaries: %i" % secondaries_to_add)
        half_autolist = int(AUTOLIST_MAX_LENGTH) / 2
        if len(new_combined) + secondaries_to_add > half_autolist:
            if secondaries_to_add > min_secondaries_to_add:
                log("Reducing secondaries to 10")
                secondaries_to_add = min_secondaries_to_add
        if len(new_combined) + secondaries_to_add < half_autolist:
            log("Bringing Watch Later to %i" % half_autolist)
            secondaries_to_add = half_autolist - len(new_combined)

        log("Secondaries to add: %i" % secondaries_to_add)
        filler_playlist_WL = filler_playlist[:int(secondaries_to_add)]
        new_autolist = new_combined + filler_playlist_WL
        new_backlog = filler_playlist[int(secondaries_to_add):]
        for vid_details in filler_playlist:
            filler_ids_added.append(vid_details['videoId'])

        log("New autolist length with fillers: %i" % len(new_autolist))

    for tier in autolist:
        if tier != '1':
            tmp_list = {}
            tmp_titles = {}
            for vid_details in autolist[tier]:
                if vid_details['videoId'] not in filler_ids_added:
                    duration = vid_details['duration']
                    hours = duration['hours']
                    minutes = duration['minutes']
                    time_tier = int(minutes / 10) if hours < 1 else 6
                    if time_tier not in tmp_list:
                        tmp_list[time_tier] = []
                        tmp_titles[time_tier] = []
                    tmp_list[time_tier].append(vid_details)
                    tmp_titles[time_tier].append(vid_details['videoTitle'])
                else:
                    log("Added to Watch Later as filler: %s: %s" % (
                    vid_details['channelTitle'], vid_details['videoTitle']))
            for time_tier in sorted(tmp_list):
                for vid_details in tmp_list[time_tier]:
                    if time_tier not in secondary_playlists:
                        secondary_playlists[time_tier] = []
                    secondary_playlists[time_tier].append(vid_details)
                    log("\t%s" % vid_details['videoTitle'])

    log("Creating XL Playlist")
    for tier in xl_autolist:
        if tier == '1':
            for id in xl_autolist[tier]:
                for vid_details in xl_autolist[tier][id]:
                    xl_combined.append(vid_details)
        else:
            for vid_details in xl_autolist[tier]:
                xl_combined.append(vid_details)

    log("Defining playlists")
    playlists = [
        {
            'name': "1) Formula 1",
            'sort': sort_f1,
            'id': F1_PLAYLIST_ID,
            'autolist': new_f1_playlist,
            'results': [],
            'deleted': []
        },
        {
            'name': "2) Watch Later",
            'sort': sort_current,
            'id': WATCH_LATER_ID,
            'autolist': new_autolist,
            'results': [],
            'deleted': []
        },
        {
            'name': "3) Backlog",
            'sort': sort_current,
            'id': BACKLOG_ID,
            'autolist': new_backlog,
            'results': [],
            'deleted': []
        },
        {
            'name': "4) XL Watch Later",
            'sort': sort_xl,
            'id': XL_ID,
            'autolist': xl_combined,
            'results': [],
            'deleted': []
        }
    ]

    for tier in secondary_playlists:
        num = str(int(tier) + 5)
        length = str((int(tier) + 1) * 10)
        playlist_name = "%s) Secondary - Under %s minutes" % (num, length)
        playlists.append(
            {
                'name': playlist_name,
                'sort': sort_secondary,
                'id': TIER_PLAYLISTS[str(tier)],
                'autolist': secondary_playlists[tier],
                'results': [],
                'deleted': []
            }
        )

    log("Placing all videos")
    final_response = {}
    for playlist in playlists:
        if playlist['sort']:
            log("Placing %s" % playlist['name'])
            final_response[playlist['name']] = {}
            data = playlist
            response = add_to_target_autolist(
                autolist=data['autolist'],
                playlist_label=playlist['name'],
                target_playlist_id=data['id'],
                already_added_ids=already_added_ids
            )

            final_response[playlist['name']]['results'] = response['results']
            final_response[playlist['name']]['deleted'] = response['deleted']
            final_response[playlist['name']]['results_count'] = len(final_response[playlist['name']]['results'])
            already_added_ids = response['already_added']

    return final_response


def add_to_target_autolist(autolist, playlist_label, target_playlist_id, already_added_ids):
    # Load the credentials from the session.
    client = get_client()

    results = []
    deleted = []
    pos = 0
    if len(autolist) > 0:
        msg = " ".join(["There are", str(len(autolist)), "items in the", playlist_label, "playlist"])
        log(msg)
        for item in autolist:
            msg_list = []
            vid_title = item['videoTitle']
            channel_title = item['channelTitle']
            if item['videoId'] not in already_added_ids:
                label = ": ".join([channel_title, vid_title])
                if item['sourcePlaylistId'] == target_playlist_id:
                    if item['position'] != pos:
                        msg_list.append("\tUpdating position:")
                        body = {
                            'id': item['playlistItemId'],
                            'snippet.playlistId': target_playlist_id,
                            'snippet.resourceId.kind': 'youtube#video',
                            'snippet.resourceId.videoId': item['videoId'],
                            'snippet.position': pos
                        }
                        if not TEST:
                            playlist_item_update_position(client, body, part='snippet')
                    else:
                        msg_list.append("\tRetaining position:")
                else:
                    msg_list = msg_list + ["\tMoving into the", playlist_label, "playlist:"]
                    body = {
                        'snippet.playlistId': target_playlist_id,
                        'snippet.resourceId.kind': 'youtube#video',
                        'snippet.resourceId.videoId': item['videoId'],
                        'snippet.position': pos
                    }
                    if not TEST:
                        response = playlist_items_insert(client, body, part='snippet')
                        body['id'] = response['id']
                        playlist_item_update_position(client, body, part='snippet')
                        playlist_items_delete(client,id=item['playlistItemId'])
                pos += 1
                results.append(label)
                already_added_ids.append(item['videoId'])
                msg_list.append(label)
            else:
                msg_list = msg_list + ["\tDeleting:", vid_title]
                deleted.append(item)
                if not TEST:
                    playlist_items_delete(client,id=item['playlistItemId'])
            log(" ".join(msg_list))

    return {
        'results': results,
        'already_added': already_added_ids,
        'deleted': deleted
    }


def playlist_items_insert(client, properties, **kwargs):
    # See full sample for function
    resource = build_resource(properties)

    # See full sample for function
    kwargs = remove_empty_kwargs(**kwargs)
    request = client.playlistItems().insert(body=resource,**kwargs)
    response = execute(request)

    return response


def playlist_item_update_position(client, properties, **kwargs):
    # See full sample for function
    resource = build_resource(properties)

    # See full sample for function
    kwargs = remove_empty_kwargs(**kwargs)
    request = client.playlistItems().update(body=resource,**kwargs)
    response = execute(request)

    return response


def playlist_items_delete(client, **kwargs):
    # See full sample for function
    kwargs = remove_empty_kwargs(**kwargs)
    request = client.playlistItems().delete(**kwargs)
    response = execute(request)
    return response


def get_playlist_items(client, autolist_id, playlist_title='autolist'):
    request = client.playlistItems().list(playlistId=autolist_id, part='contentDetails', maxResults=50)
    vids = []
    page = 1
    print("Fetching " + playlist_title, end=": ")
    position = 0
    while request is not None:
        response = execute(request)

        next_page_token = response['nextPageToken'] if 'nextPageToken' in response else None
        items = response['items']
        for item in items:
            item['snippet'] = {}
            item['snippet']['playlistId'] = autolist_id
            item['snippet']['position'] = position
            position += 1
            vids.append(item)

        request = client.playlistItems().list(playlistId=autolist_id, part='contentDetails', maxResults=50, pageToken=next_page_token) if next_page_token is not None else None

        page += 1
    print(str(len(vids)) + " items found")
    return vids


def build_resource(properties):
  resource = {}
  for p in properties:
    # Given a key like "snippet.title", split into "snippet" and "title", where
    # "snippet" will be an object and "title" will be a property in that object.
    prop_array = p.split('.')
    ref = resource
    for pa in range(0, len(prop_array)):
      is_array = False
      key = prop_array[pa]

      # For properties that have array values, convert a name like
      # "snippet.tags[]" to snippet.tags, and set a flag to handle
      # the value as an array.
      if key[-2:] == '[]':
        key = key[0:len(key)-2:]
        is_array = True

      if pa == (len(prop_array) - 1):
        # Leave properties without values out of inserted resource.
        if properties[p]:
          if is_array:
            ref[key] = properties[p].split(',')
          else:
            ref[key] = properties[p]
      elif key not in ref:
        # For example, the property is "snippet.title", but the resource does
        # not yet have a "snippet" object. Create the snippet object here.
        # Setting "ref = ref[key]" means that in the next time through the
        # "for pa in range ..." loop, we will be setting a property in the
        # resource's "snippet" object.
        ref[key] = {}
        ref = ref[key]
      else:
        # For example, the property is "snippet.description", and the resource
        # already has a "snippet" object.
        ref = ref[key]
  return resource


def remove_empty_kwargs(**kwargs):
  good_kwargs = {}
  if kwargs is not None:
    for key, value in kwargs.items():
      if value:
        good_kwargs[key] = value
  return good_kwargs


def execute(request_object):
    has_result = False
    wait_time = 0
    retry_count = 0
    response = request_object.execute()
    has_result = True
    return response
    # while retry_count < 3 and not has_result:
    #     try:
    #         response = request_object.execute()
    #         has_result = True
    #         return response
    #     except HttpError as e:
    #         if e.resp.status in ERROR_CODES and retry_count < 3:
    #             has_result = False
    #             # log(json.loads(e.content.decode('utf-8'))['error']['message'])
    #             if wait_time < 60:
    #                 wait_time += 10
    #             msg = " ".join(
    #                 [
    #                     "Waiting",
    #                     str(wait_time),
    #                     "seconds before retrying"
    #                 ]
    #             )
    #             log(msg)
    #             sleep(wait_time)
    #             log("Retrying now...")
    #             retry_count += 1
    #             continue
    #         else:
    #             print("e.resp.status: %s" % str(e.resp.status))
    #             print("e.content: %s" % e.content)
    #             print("e.error.details: %s" % str(e.error_details))
    #             print("e: %s" % str(e))
    #             raise


kwargs = {
    "sort_current": True,
    "sort_f1": True,
    "import_queue": True,
    "sort_secondary": False,
    "sort_xl": False,
    "sort": False
}
merge_sort_split_v2(**kwargs)