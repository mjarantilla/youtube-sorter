from handlers.playlist import YoutubePlaylist
from handlers.videos import Video
from handlers.ranks import RanksHandler
from handlers.cache import VideoCache
from handlers.client import YoutubeClientHandler
from handlers.utilities import Logger, ConfigHandler, print_json
import json
import datetime
import math
import os.path
from time import sleep


logger = Logger()
logger.write("--------------------------------------------")
logger.write("STARTING ORGANIZATION OF YOUTUBE PLAYLISTS")
logger.write("--------------------------------------------", delim=True)
logger.write("Initializing caches and configs")
cache = VideoCache()
config = ConfigHandler()
ranks = RanksHandler()
client = YoutubeClientHandler('sorter.pickle')
logger.write("Initialization of objects complete", delim=True, header=True)


# SORTING FUNCTIONS
def assemble_local_playlists(primary_playlist_name, backlog_name, queue_name, playlist_map, result, backlog, remainder, queue_remainder):
    logger.write("Adding to primary", header=True)
    primary_playlist_id = playlist_map[primary_playlist_name]
    backlog_id = playlist_map[backlog_name]
    queue_id = playlist_map[queue_name]
    outputs = {
        primary_playlist_name: {
            'playlist_id': primary_playlist_id,
            'videos': [],
            'backlog': False,
            'queue': False
        },
        backlog_name: {
            'playlist_id': backlog_id,
            'videos': [],
            'backlog': True,
            'queue': False
        },
        queue_name: {
            'playlist_id': queue_id,
            'videos': [],
            'backlog': False,
            'queue': True
        }
    }

    for video in result:
        output_entry = {
            "title": video.title,
            "url": "https://www.youtube.com/watch?v=%s" % video.id,
            "vid_id": video.id,
            "vid_source": video.metadata
        }

        outputs[primary_playlist_name]['videos'].append(output_entry)

    logger.write("Adding to backlog", header=True)
    i = 0
    for video in reversed(backlog):
        output_entry = {
            "title": video.title,
            "url": "https://www.youtube.com/watch?v=%s" % video.id,
            "vid_id": video.id,
            "vid_source": video.metadata
        }
        outputs[backlog_name]['videos'].insert(0, output_entry)

    for video in remainder:
        outputs[backlog_name]['videos'].append({
            "title": video.title,
            "url": "https://www.youtube.com/watch?v=%s" % video.id,
            "vid_id": video.id,
            "vid_source": video.metadata
        })

    for video in queue_remainder:
        outputs[queue_name]['videos'].append({
            "title": video.title,
            "url": "https://www.youtube.com/watch?v=%s" % video.id,
            "vid_id": video.id,
            "vid_source": video.metadata
        })

    outputs_fp = open(os.path.join(config.variables['CACHE_DIR'], 'outputs.json'), mode='w')
    print_json(outputs, fp=outputs_fp)
    outputs_fp.close()


def sort(playlist_map, playlists, primary_tier, filler_tier=None):
    """

    @param playlist_map:
    @param playlists:
    @param primary_tier:
    @param filler_tier:
    @return:
                result:             The actual playlist, including any filler videos that had been added
                overflow:           The videos that need to be added to the backlog
                remainder:          The unused filler items, less what has been added to the result list
                queue_remainder:    The videos that are still in the queue playlist
    """

    logger.write("BEGINNING SORTING")
    logger.write("Merging playlists")

    logger.write("Reading subscriptions.json")
    subs_fp = open(config.variables['SUBSCRIPTIONS_FILE'], mode="r")
    subscriptions = json.load(subs_fp)['details']
    subs_fp.close()

    logger.write("Setting max and min lengths")
    max_length = config.variables['AUTOLIST_MAX_LENGTH']
    min_length = math.ceil(max_length / 2)
    max_filler = config.variables['FILLER_LENGTH']

    logger.write("Initializing playlists")

    playlist_videos = get_videos(playlists)

    queue_ids = []
    for video in playlists['queue'].videos:
        queue_ids.append(video['contentDetails']['videoId'])

    logger.write("SORTING primary tier videos in current playlists", header=True)
    playlists_to_include = {
        playlist_map['primary']: playlist_videos[playlist_map['primary']],
        playlist_map['queue']: playlist_videos[playlist_map['queue']]
    }
    if filler_tier is not None:
        playlists_to_include[playlist_map[filler_tier]] = playlist_videos[playlist_map[filler_tier]]

    primary = determine_tier_videos(
        playlist_videos=playlists_to_include,
        tier_name=primary_tier,
        subscriptions=subscriptions,
        cache=cache
    )
    logger.write("DONE sorting primary tier videos", delim=True)

    # filler_in_primary = []
    all_filler = []
    if filler_tier is not None:
        # logger.write("SORTING filler videos in queue and watch later playlists")
        # filler_in_primary = determine_tier_videos(
        #     playlist_videos={
        #         playlist_map[primary_tier]: playlist_videos[playlist_map[primary_tier]],
        #         playlist_map['queue']: playlist_videos[playlist_map['queue']]
        #     },
        #     tier_name=filler_tier,
        #     cache=cache,
        #     subscriptions=subscriptions,
        #     date_sorting=True
        # )
        # logger.write("DONE sorting filler videos in queue and watch later", delim=True)
        logger.write("SORTING filler videos in current playlists")
        all_filler = determine_tier_videos(
            playlist_videos=playlists_to_include,
            tier_name=filler_tier,
            cache=cache,
            subscriptions=subscriptions,
            date_sorting=True
        )
        logger.write("DONE sorting ALL filler videos", delim=True)

    # combined = primary + filler_in_primary
    combined = primary

    result, overflow, remainder = calculate_overflow(original_playlist=combined, filler=all_filler, max_len=max_length,
                                                     min_len=min_length, max_fill=max_filler)

    queue_remainder = []
    total = result + overflow + remainder
    total_ids = []
    for video in total:
        total_ids.append(video.id)

    for vid_id in queue_ids:
        if vid_id not in total_ids:
            queue_remainder.append(Video(id=vid_id, cache=cache, client=client))

    logger.write("Total items: %i" % (len(result + overflow)), header=True)
    logger.write("Items in main playlist: %i" % len(result))
    logger.write("Items to be added to overflow: %i" % len(overflow))
    logger.write("Items to be left in queue: %i" % len(queue_remainder), delim=True)

    return result, overflow, remainder, queue_remainder


def determine_tier_videos(playlist_videos, tier_name, subscriptions, date_sorting=False, **kwargs):
    """

    @param playlists:               A list of YoutubePlaylist() objects for each Youtube playlist that need to be merged
    @param tier_name:               The name of the tier as taken from ranks.json
    @param subscriptions:           The contents of the subscriptions.json file
    @param date_sorting:            If True, this function will ignore channel tier sorting and will only sort by date
    @param kwargs:                  An catchall for any other kwargs that may be passed into the function
    @return:                        Returns the final sorted list of videos for the target playlist
    """

    logger.write("Getting playlist videos", tier=1)
    sorted_channel_ids = sort_channels_by_tier(tier_name, subscriptions)

    logger.write("Combining playlist videos", tier=1)
    combined_unsorted = []
    for playlist_id in playlist_videos:
        combined_unsorted += playlist_videos[playlist_id]
    combined_unsorted = sort_by_date(combined_unsorted)

    combined_sorted = []
    if not date_sorting:
        # Sorts the videos by their published date and then by their channel IDs
        channel_video_map = {}
        for video in combined_unsorted:
            channel_id = video.data['snippet']['channelId']
            if channel_id not in channel_video_map:
                channel_video_map[channel_id] = []
            channel_video_map[channel_id].append(video)

        # Creates a consolidated list of videos sorted by channel
        for channel_id in sorted_channel_ids:
            if channel_id in channel_video_map:
                for video in channel_video_map[channel_id]:
                    combined_sorted.append(video)
    else:
        for video in combined_unsorted:
            channel_id = video.data['snippet']['channelId']
            if channel_id in sorted_channel_ids:
                combined_sorted.append(video)

    return combined_sorted


def filter_invalid_videos(video_list):
    """
    Filters videos that are too long or too short and videos that are "private" on YouTube

    @param video_list: A list of Video() objects
    @return:
    """
    valid_vids = []

    for video in video_list:
        if check_validity(video):
            valid_vids.append(video)

    return valid_vids


def check_validity(video):
    """
    Checks the validity of a given Video() object based on the criteria specified in config.json

    @param video:   A Video() object
    @return:        True or False
    """

    min_duration_sec = convert_to_seconds(config.variables['VIDEO_MIN_DURATION'])
    max_duration_sec = convert_to_seconds(config.variables['VIDEO_MAX_DURATION'])

    if not video.private:
        seconds = video.duration

        if min_duration_sec < seconds < max_duration_sec:
            return True

    logger.write("Rejecting %s" % video.title, tier=3)
    return False


def sort_by_date(video_list):
    """
    @param video_list:  An unsorted list of Video() objects
    @return:            A list of Video() objects sorted by date published
    """
    logger.write("Sorting by date", tier=2)
    date_map = {}
    for video in video_list:
        published_date = datetime.datetime.strptime(video.data['snippet']['publishedAt'],
                                                    "%Y-%m-%dT%H:%M:%SZ").timestamp()
        date_map[published_date] = video

    sorted_list = []
    for entry in sorted(date_map.items()):
        sorted_list.append(entry[1])

    return sorted_list


def calculate_overflow(original_playlist, filler, max_len, min_len, max_fill=10):
    """
    Calculates how many videos to send to the overflow playlist

    @param original_playlist:   The playlist to calculate overflow for
    @param max_len:             The maximum length that the playlist can be before overflow videos are removed
    @param min_len:             The minimum length that the playlist can be before filler videos are added
    @param max_fill:            The maximum number of filler videos to add to the original playlist
    @param backlog:             The destination of the overflowed videos and the source for the filler videos
    @return:
    """

    logger.write("Calculating overflow items", tier=1)
    overflow = []
    remainder = []

    if len(original_playlist) > max_len:
        primary = original_playlist[:max_len]
        overflow = original_playlist[max_len:]
        remainder = filler
    else:
        primary = original_playlist
        if len(original_playlist) < min_len:
            filler_to_add = min_len - len(original_playlist)
        else:
            filler_to_add = max_fill if max_len - len(original_playlist) > max_fill \
                else max_len - len(original_playlist)
        filler_added = 0
        logger.write("Filler to add: %s" % filler_to_add, tier=2)
        while filler_added < len(filler) and filler_added < filler_to_add:
            primary.append(filler[filler_added])
            filler_added += 1

        remainder = filler[filler_added:]

    return primary, overflow, remainder


def fetch_playlists(playlist_map):
    playlists = {}
    inputs = {}
    logger.write("Fetching playlists")
    for playlist_name in playlist_map:
        playlist_id = playlist_map[playlist_name]
        playlists[playlist_name] = YoutubePlaylist(playlist_id, cache=cache, client=client)
        playlists[playlist_name].get_playlist_items()

        inputs[playlist_name] = {
            "playlist_id": playlist_id,
            "videos": []
        }
        for playlist_item in playlists[playlist_name].videos:
            inputs[playlist_name]['videos'].append({
                "title": playlist_item['snippet']['title'],
                "url": "https://www.youtube.com/watch?v=%s" % playlist_item['contentDetails']['videoId'],
                "vid_id":  playlist_item['contentDetails']['videoId'],
                "vid_source": {
                    "source_playlist_id": playlist_id,
                    "source_playlist_name": playlists[playlist_name].title,
                    "source_playlist_position": playlist_item['snippet']['position']
                }
            })

    logger.write("Writing inputs.json")
    inputs_fp = open(os.path.join(config.variables['CACHE_DIR'], "inputs.json"), mode='w')
    print_json(inputs, fp=inputs_fp)
    inputs_fp.close()

    logger.write("DONE fetching all playlists.", delim=True)
    return playlists


# COMMAND FUNCTIONS
def sequencer(starting_playlist, ending_playlist, removals, test=False):
    def test_seq():
        counter = 0
        logger.write("Original\t\tPrevious\t\t|Current\t\t\tEndstate", tier=1)
        while counter < len(interim_playlist_videos):
            if counter == i:
                logger.write("------------------------------------------------------------------------------------------------")
            orig_vid_name = starting_playlist_videos[counter]['title'][:12] if counter < len(starting_playlist_videos) else "\t"
            prev_vid_name = previous_playlist_videos[counter]['title'][:12] if counter < len(previous_playlist_videos) else "\t"
            interim_vid_name = interim_playlist_videos[counter]['title'][:12]
            ending_vid_name = ending_playlist_videos[counter]['title'][:12] if counter < len(ending_playlist_videos) else "\t"
            logger.write("(%s) %s\t(%s) %s\t| (%s) %s\t(%s) %s" % (counter, orig_vid_name, counter, prev_vid_name, counter, interim_vid_name, counter, ending_vid_name))
            if counter == i:
                logger.write("------------------------------------------------------------------------------------------------")
            counter += 1
        logger.write()
        print(i, command['action'], command['from'] if 'from' in command else "", command['to'] if 'to' in command else "")
        input()

        # j = 0
        # for interim_vid in interim_playlist_videos:
        #     if interim_vid['vid_id'] == endstate_vid_id:
        #         actual_source_position = j
        #         interim_playlist_videos.pop(j)
        #         command_counts['video'] = endstate_vid['title']
        #         command_counts['expected'] = {
        #             "actual_source_position": j,
        #             "expected source position": source_position,
        #             "original source position": original_source_pos,
        #             "ending position": i
        #         }
        #         command_counts["videos"] = []
        #         k = 0
        #         for vid in interim_playlist_videos.copy():
        #             command_counts["videos"].append("(%s) %s" % (k, vid['title']))
        #             k += 1
        #         assert j == source_position, print_json(command_counts)
        #     j += 1

    log_tier = 1

    starting_playlist_id = starting_playlist['playlist_id']
    starting_playlist_videos = starting_playlist['videos']
    ending_playlist_id = ending_playlist['playlist_id']
    interim_playlist_videos = starting_playlist['videos'].copy()
    previous_playlist_videos = interim_playlist_videos.copy()
    ending_playlist_videos = ending_playlist['videos']
    playlist_id = ending_playlist['playlist_id']
    backlog = ending_playlist['backlog']
    queue = ending_playlist['queue']

    command_sequence = []
    command = {"action": None}
    command_counts = {
        'import': 0,
        'update': 0,
        'none': 0
    }
    i = 0
    imports = 0

    """ Remove duplicates first"""
    duplicates = identify_duplicates(search_videos=interim_playlist_videos)

    remove_duplicates(duplicates=duplicates, test=test)

    duplicates = identify_duplicates(search_videos=ending_playlist_videos, reference_list=interim_playlist_videos)

    remove_duplicates(duplicates=duplicates, test=test)

    """ Begin sorting/importing """
    for video in ending_playlist_videos:
        if not video:
            continue
        assert 'vid_source' in video and video['vid_source'], print_json(video)

        source_playlist_id = video['vid_source']['source_playlist_id']
        source_position = video['vid_source']['source_playlist_position']
        playlist_item_id = video['vid_source']['source_playlist_item_id'] \
            if 'source_playlist_item_id' in video['vid_source'] else None

        endstate_vid = ending_playlist_videos[i]
        endstate_vid_id = ending_playlist_videos[i]['vid_id']
        previous_playlist_videos = interim_playlist_videos.copy()

        if i < len(interim_playlist_videos):
            interim_vid_id = interim_playlist_videos[i]['vid_id']

            """ Command definition """
            if source_playlist_id != ending_playlist_id:
                interim_playlist_videos.insert(i, video)
                imports += 1
                command = {
                    "action": "import",
                    "from": {
                        "playlist": source_playlist_id,
                    },
                    "to": {
                        "playlist": ending_playlist_id,
                        "position": i if not backlog and not queue else 0
                    }
                }
                command_counts["import"] += 1
            else:
                if interim_vid_id != endstate_vid_id:
                    actual_source_position = 0
                    for interim_vid in interim_playlist_videos:
                        if interim_vid['vid_id'] == endstate_vid_id:
                            interim_playlist_videos.pop(actual_source_position)
                        actual_source_position += 1
                    interim_playlist_videos.insert(i, endstate_vid)

                    command = {
                        "action": "update",
                        "playlist_item_id": playlist_item_id,
                        "from": {
                            "playlist": ending_playlist_id
                        },
                        "to": {
                            "playlist": ending_playlist_id,
                            "position": i
                        }
                    }
                    command_counts["update"] += 1

                else:
                    command = {"action": None}
                    command_counts["none"] += 1
        else:
            if source_playlist_id != ending_playlist_id:
                interim_playlist_videos.insert(i, video)
                imports += 1
                command = {
                    "action": "import",
                    "from": {
                        "playlist": source_playlist_id,
                    },
                    "to": {
                        "playlist": ending_playlist_id,
                        "position": i if not backlog and not queue else 0
                    }
                }
                command_counts["import"] += 1

        """ Actual execution of the command """
        if not test:
            if command['action']:
                vid_obj = Video(video['vid_id'], cache=cache, client=client)
                if command['action'] == "update":
                    if not backlog and not queue:
                        logger.write("Executing command: %s" % command['action'], tier=log_tier)
                        kwargs = {
                            'playlist_item_id': command['playlist_item_id'],
                            'playlist_id': command['to']['playlist'],
                            'position': command['to']['position'],
                            'test': test
                        }
                        logger.write("Updating position to pos %s: %s" % (command['to']['position'], vid_obj.title), tier=1)
                        sleep(0.2)
                        vid_obj.update_playlist_position(**kwargs)
                elif command['action'] == "import":
                    logger.write("Executing command: %s" % command['action'], tier=log_tier)
                    kwargs = {
                        'playlist_id': command['to']['playlist'],
                        'position': command['to']['position'],
                        'test': test
                    }
                    logger.write("Importing into position %s: %s" % (command['to']['position'], vid_obj.title), tier=1)
                    sleep(0.2)
                    vid_obj.add_to_playlist(**kwargs)
        i += 1

    videos_to_remove = []
    for video in interim_playlist_videos:
        vid_id = video['vid_id']
        member = False
        for ending_vid in ending_playlist_videos:
            ending_vid_id = ending_vid['vid_id']
            if ending_vid_id == vid_id:
                member = True
        if not member:
            videos_to_remove.append(video)

    for video in videos_to_remove:
        if not test and not backlog:
            logger.write("Executing command: remove", tier=log_tier)
            vid_obj = Video(video['vid_id'], cache=cache, client=client)
            playlist_item_id = video['vid_source']['source_playlist_item_id']
            playlist_id = video['vid_source']['source_playlist_id']
            vid_obj.remove_from_playlist(playlist_id=playlist_id, playlist_item_id=playlist_item_id)
    print_json(command_counts)
    cache.write_cache()


def identify_duplicates(search_videos, reference_list=None):
    logger.write("Identifying duplicates", tier=1)
    duplicates = {}
    item_ids = []
    if reference_list is None:
        reference_list = search_videos.copy()
    for video in reference_list:
        dupes = identify_duplicates_of_video(video, search_videos)
        for dupe in dupes:
            playlist_id = dupe[1]['vid_source']['source_playlist_id']
            item_id = dupe[1]['vid_source']['source_playlist_item_id']
            if item_id not in item_ids:
                item_ids.append(item_id)
                if playlist_id not in duplicates:
                    duplicates[playlist_id] = {}
                if dupe[1]['vid_id'] not in duplicates[playlist_id]:
                    duplicates[playlist_id][dupe[1]['vid_id']] = []
                duplicates[playlist_id][dupe[1]['vid_id']].append(dupe)
                if not duplicates[playlist_id][video['vid_id']]:
                    duplicates[playlist_id].pop(video['vid_id'])

    return duplicates


def identify_duplicates_of_video(search_video, playlist_videos):
    instances = []
    duplicates = []
    index = 0
    for video in playlist_videos:
        if search_video['vid_id'] == video['vid_id']:
            if video['vid_id'] not in instances:
                instances.append((video['vid_source']['source_playlist_position'], video))
            else:
                duplicates.append((video['vid_source']['source_playlist_position'],video))
                logger.write("%s at %s" % (video['title'], video['vid_source']['source_playlist_position']), tier=2)
        index += 1
    if len(instances) > 0:
        instances.pop(0)

    return instances


def remove_duplicates(duplicates, test=False):
    logger.write("Removing duplicates", tier=1)
    for playlist_id in duplicates:
        for vid_id in duplicates[playlist_id]:
            dupes = duplicates[playlist_id][vid_id]
            for dupe in dupes:
                index, vid_data = dupe
                logger.write("index %s:\t %s" % (index, vid_data['title']), tier=2)
                vid_id = vid_data['vid_id']
                video = Video(vid_id, cache=cache, client=client)

                video.remove_from_playlist(
                    playlist_item_id=vid_data['vid_source']['source_playlist_item_id'],
                    already_checked=True,
                    test=test
                )


# VIDEO/PLAYLIST FETCHING FUNCTIONS
def get_videos(playlists):
    logger.write("Fetching video info for all videos in playlists", tier=1)
    playlist_videos = {}
    for playlist in playlists:
        playlist_handler = playlists[playlist]
        logger.write("Filtering invalid videos for %s" % playlist, tier=2)
        playlist_videos[playlist_handler.id] = filter_invalid_videos(get_playlist_videos(playlist_handler))
    logger.write("DONE fetching video info", delim=True)
    return playlist_videos


def get_channel_index(subscriptions):
    logger.write("Fetching channel subscriptions", tier=2)
    channel_index = {}
    for channel_title in subscriptions:
        channel_info = subscriptions[channel_title]
        channel_id = channel_info['id']
        channel_index[channel_id] = channel_title
    logger.write("DONE fetching channel subscriptions", tier=2, delim=True)
    return channel_index


def sort_channels_by_tier(tier_name, subscriptions):
    # Sorts the channel IDs into a list based on tier
    channel_list = get_tier_channels(tier_name)
    logger.write("Sorting channel IDs by tier", tier=2)
    sorted_channel_ids = []
    for channel_name in channel_list:
        channel_id = subscriptions[channel_name]['id']
        sorted_channel_ids.append(channel_id)
    logger.write("DONE sorting channel IDs by tier", tier=2, delim=True)

    return sorted_channel_ids


def get_playlist_videos(playlist_handler):
    """

    @param playlist_handler:    The YoutubePlaylist() object for the playlist to get the videos of
    @return:                    Returns a list of Video() objects presumably ordered by their positions in the playlist
    """

    playlist_videos = []
    for playlist_item in playlist_handler.videos:
        vid_id = playlist_item['contentDetails']['videoId']
        vid_position = playlist_item['snippet']['position']
        vid_kwarg = {
            'id': vid_id,
            'cache': cache,
            'client': client
        }
        video = Video(**vid_kwarg)
        video.metadata = {
            'source_playlist_id': playlist_handler.id,
            'source_playlist_name': playlist_handler.title,
            'source_playlist_position': vid_position,
            'source_playlist_item_id': playlist_item['id']
        }
        playlist_videos.append(video)

    return playlist_videos


def get_tier_channels(tier_name):
    """
    Fetches a list of channels for a given tier name

    @param tier_name:   The name of the tier whose channels to fetch
    @return:            Returns a list of channel names
    """
    handler = RanksHandler()
    handler.define_ranks()

    specified_tier = None
    for tier in handler.rank_data:
        if tier.name == tier_name:
            specified_tier = tier

    channels = specified_tier.get_channels()

    return channels


# UTILITY FUNCTIONS
def convert_to_seconds(time_map):
    seconds = 0
    if 'SECONDS' in time_map:
        seconds += int(time_map['SECONDS'])
    if 'MINUTES' in time_map:
        seconds += int(time_map['MINUTES']) * 60
    if 'HOURS' in time_map:
        seconds += int(time_map['HOURS']) * 60 * 60
    if 'DAYS' in time_map:
        seconds += int(time_map['DAYS']) * 24 * 60 * 60
    return seconds


# VERIFICATION FUNCTIONS
def verify(skip_wait=False):
    """
    Read-only function

    @return:    A dictionary containing corrections that need to be made
    """
    if not skip_wait:
        logger.write("WAITING TO START VERIFICATION")
        counter = 0
        while counter < 15:
            if counter % 5 == 0:
                logger.write(".")
            sleep(1)
            counter += 1

    log_tier = 1
    logger.write("BEGINNING VERIFICATION", tier=log_tier)

    outputs_fp = open(os.path.join(config.variables['CACHE_DIR'], 'outputs.json'))
    outputs = json.load(outputs_fp)
    outputs_fp.close()
    corrections = {}

    for playlist in outputs:
        corrections[playlist] = {}

        logger.write("Verifying Playlist %s" % str(playlist).capitalize(), tier=log_tier+1)
        playlist_data = outputs[playlist]
        corrections[playlist] = verify_local_vs_youtube(playlist_data=playlist_data, playlist_name=playlist, skip_wait=skip_wait)
        logger.write("DONE", tier=log_tier+1, delim=True)

    corrections_fp = open(os.path.join(config.variables['CACHE_DIR'], 'corrections.json'), mode="w")
    print_json(corrections, fp=corrections_fp)
    corrections_fp.close()

    return corrections


def verify_local_vs_youtube(playlist_data, playlist_name='', skip_wait=False):
    """
    A simpler replacement for verify_playlist_contents

    @param playlist_data:   The playlist dictionary to be compared
    @param playlist_name:   The arbitrary name of the playlist

    @return:
    """
    if not skip_wait:
        logger.write("WAITING TO START VERIFICATION")
        counter = 0
        while counter < 15:
            if counter % 5 == 0:
                logger.write(".")
            sleep(1)
            counter += 1

    reference_playlist = playlist_data['videos']
    playlist_id = playlist_data['playlist_id']
    backlog = playlist_data['backlog']
    queue = playlist_data['queue']

    log_tier = 2
    logger.write("Comparing actual playlist with expected playlist", tier=log_tier)
    playlist_info = {
        'backlog': backlog,
        'queue': queue,
        'playlist_id': playlist_id,
        'actual': [],
        'videos': []
    }

    """ Fetches playlist from Youtube and formats it into a compatible JSON """
    playlist = YoutubePlaylist(id=playlist_id, cache=cache, client=client)
    playlist.get_playlist_items()

    for playlist_item in playlist.videos:
        playlist_vid_id = playlist_item['contentDetails']['videoId']
        vid_data = {
            'title': playlist_item['snippet']['title'],
            'vid_id': playlist_vid_id,
            'url': "https://www.youtube.com/watch?v=%s" % playlist_vid_id,
            'vid_source': {
                'source_playlist_id': playlist.id,
                'source_playlist_name': playlist.title,
                'source_playlist_position': playlist_item['snippet']['position'],
                'source_playlist_item_id': playlist_item['id']
            }
        }
        playlist_info['actual'].append(vid_data)

    """ 
    Checks for videos that are present but out of place.
    
    When found, the existing playlist info in vid_source 
    """
    logger.write("Checking for videos in output that are in the playlist but in the wrong position", tier=log_tier+1)
    iteration = 0
    for vid_data in reference_playlist:
        counter = 0
        for input_vid_data in playlist_info['actual']:
            if vid_data['vid_id'] == input_vid_data['vid_id']:
                """ If found, playlist info in vid_source is overwritten with the current playlist info """
                vid_data['vid_source'] = input_vid_data['vid_source']
            counter += 1
        iteration += 1
    logger.write("DONE", tier=log_tier + 1, delim=True)
    playlist_info['diff'] = False

    """ Might be unnecessary """
    i = 0
    logger.write("Beginning comparison", tier=log_tier+1)
    while i < len(playlist_info['actual']) or i < len(reference_playlist):
        current_vid_data = playlist_info['actual'][i] if i < len(playlist_info['actual']) else {'vid_id': None}
        expected_vid_data = reference_playlist[i] if i < len(reference_playlist) else {'vid_id': None}
        # if current_vid_data['vid_id'] != expected_vid_data['vid_id']:
        #     playlist_info['diff'] = True
        if expected_vid_data['vid_id'] is not None:
            playlist_info['videos'].append(expected_vid_data)
        i += 1
    logger.write("DONE", tier=log_tier+1, delim=True)

    """ Count how many changes need to be made """
    playlist_info['corrections'] = count_corrections_needed(reference_playlist=reference_playlist, playlist=playlist,
                                                            playlist_name=playlist_name, backlog=backlog, queue=queue)

    playlist_info['diff'] = 0
    for item in ['add', 'move', 'remove']:
        playlist_info['diff'] += len(playlist_info['corrections'][item])

    if playlist_info['diff']:
        logger.write("Differences found", tier=log_tier)
    else:
        logger.write("No differences found", tier=log_tier, delim=True)

    return playlist_info


def count_corrections_needed(reference_playlist, playlist_id=None, playlist=None, playlist_name='', backlog=False, queue=False):
    """
    Verifies that the actual playlist on YouTube matches the intended output as defined by the output_list

    @param reference_playlist:     The intended playlist
    @param playlist_id:     The playlist ID of the actual Youtube playlist
    @param playlist_name:   The arbitrary name of the playlist
    @param backlog:         A boolean flag designating whether the playlist should be treated as a backlog. If treated
                            as a backlog, videos will not be removed.
    @return:                Returns a dictionary of corrective actions
    """
    log_tier = 3
    logger.write("Determining video membership corrections for %s" % playlist_name, tier=log_tier)
    corrections = {
        'add': [],
        'remove': [],
        'move': []
    }
    playlist_info = {
        'backlog': backlog,
        'queue': queue,
        'playlist_id': playlist_id,
        'input': [],
        'output': []
    }
    assert playlist_id or playlist, "Must pass either playlist_id or a YoutubePlaylist() object as a parameter"

    if playlist is None:
        playlist = YoutubePlaylist(id=playlist_id, cache=cache, client=client)
        playlist.get_playlist_items()
    else:
        playlist = playlist

    for playlist_item in playlist.videos:
        playlist_vid_id = playlist_item['contentDetails']['videoId']
        vid_data = {
            'title': playlist_item['snippet']['title'],
            'vid_id': playlist_vid_id,
            'url': "https://www.youtube.com/watch?v=%s" % playlist_vid_id,
            'vid_source': {
                'source_playlist_id': playlist.id,
                'source_playlist_name': playlist.title,
                'source_playlist_position': playlist_item['snippet']['position']
            }
        }
        playlist_info['input'].append(vid_data)

    index = 0
    for vid_snippet in reference_playlist:
        video = Video(id=vid_snippet['vid_id'], cache=cache, client=client)
        correction = video_needs_correction(video, index, playlist, backlog, queue)
        if correction:
            for key in correction:
                correction_data = correction[key]
                for action in correction_data:
                    corrections[key].append(action)
        index += 1

    output_vid_ids = []

    for vid_snippet in reference_playlist:
        output_vid_ids.append(vid_snippet['vid_id'])

    if not backlog:
        """Remove videos that are in the playlist but shouldn't be"""

        for playlist_item in playlist.videos:
            playlist_vid_id = playlist_item['contentDetails']['videoId']
            if playlist_vid_id not in output_vid_ids:
                corrections['remove'].append(
                    {
                        'vid_id': playlist_vid_id,
                        'playlist_id': playlist.id,
                        'title': playlist_item['snippet']['title'],
                        'position': playlist_item['snippet']['position']
                    }
                )

    logger.write("The following videos need to be corrected for playlist %s:" % playlist_name, tier=log_tier)
    for action in corrections:
        vid_list = corrections[action]
        # if action == 'move':
        #     logger.write("- %s: %s" % (action, len(corrections['move']) > 0), tier=log_tier)
        # else:
        logger.write("- %s" % action, tier=log_tier)
        for correction in vid_list:
            title = correction['title']
            if action == 'move':
                logger.write("\t- %s from %s to %s" % (title, correction['actual'], correction['recorded']), tier=log_tier)
            else:
                logger.write("\t- %s" % title, tier=log_tier)
        logger.write()
    logger.write("DONE making list of corrections", tier=log_tier, delim=True)
    playlist_info['actions'] = corrections

    return corrections


def video_needs_correction(video, index, playlist_handler, backlog=False, queue=False):
    playlist_id = playlist_handler.id
    cached_membership_records = video.data['playlist_membership']
    actual_membership = None
    corrective_action = None
    recorded_membership = {
        "vid_id": video.id,
        "position": index,
        "playlist_id": playlist_handler.id
    }
    corrective_action = {}
    """
    Checks the cache for playlist membership
    """
    if playlist_id in cached_membership_records:
        cached_playlist_membership = cached_membership_records[playlist_id]

    """
    Fetches playlist and checks whether the video is present. Also removes all duplicates from the playlist.
    """
    playlist_items = video.check_playlist_membership(playlist_id, playlist_handler, verify_only=True)
    if len(playlist_items) > 0:
        pl_item = playlist_items[0]
        pl_item_id = pl_item['id']
        pl_item_position = pl_item['snippet']['position']
        actual_membership = {
            'playlist_item_id': pl_item_id,
            'position': pl_item_position
        }

    if len(playlist_items) > 1:
        corrective_action["remove"] = []
        for playlist_item in playlist_items[1:]:
            position = playlist_item['snippet']['position']
            item_id = playlist_item['id']
            corrective_action["remove"].append(
                {
                    "vid_id": video.id,
                    "playlist_id": playlist_id,
                    "playlist_item_id": item_id,
                    "position": position,
                    "title": playlist_item['snippet']['title']
                }
            )

    if actual_membership:
        if recorded_membership['position'] != actual_membership['position'] and not backlog and not queue:
            corrective_action['move'] = [
                    {
                        "vid_id": video.id,
                        "playlist_id": playlist_id,
                        "playlist_item_id": actual_membership['playlist_item_id'],
                        "recorded": recorded_membership['position'],
                        "actual": actual_membership['position'],
                        "title": video.title
                    }
            ]
    else:
        corrective_action['add'] = [
            {
                "vid_id": video.id,
                "playlist_id": playlist_id,
                "position": recorded_membership['position'],
                "title": video.title
            }
        ]

    return corrective_action


def correct(corrections, test=False):
    """
    This function is active. Must have a test flag.

    @param corrections:
    @param test:            If True, this function will not execute anything
    @return:
    """
    for playlist_id in corrections:
        logger.write("Correcting playlist ID: %s" % playlist_id)
        corrective_actions = corrections[playlist_id]['actions']
        backlog = corrections[playlist_id]['backlog']
        logger.write("Backlog: %s" % backlog)
        for action in corrective_actions:
            if action != 'move':
                logger.write(action, tier=1)
                for vid_snippet in corrective_actions[action]:
                    if test:
                        logger.write("- %s" % vid_snippet['title'], tier=1)
                    else:
                        vid_id = vid_snippet['vid_id']
                        playlist_id = vid_snippet['playlist_id']
                        position = vid_snippet['position']
                        video = Video(id=vid_id, cache=cache, client=client)
                        if action == 'add':
                            video.add_to_playlist(playlist_id=playlist_id, position=position, test=test)
                        elif action == 'remove':
                            if not backlog:
                                video.remove_from_playlist(playlist_id=playlist_id, already_checked=True, test=test)
            logger.write()
        logger.write()

    return False


def correct_playlists(playlists, test=False):
    corrections = json.load(open(os.path.join(config.variables['CACHE_DIR'], 'corrections.json')))
    for playlist in playlists:
        playlist_name = playlist['name']
        if playlist_name in corrections:
            playlist_data = corrections[playlist_name]
            correct_playlist(playlist_name, playlist_data, test)


def correct_playlist(playlist_name, playlist_data, test=False):
    diff = playlist_data['diff']
    iter = 0
    iter_limit = 5
    while diff and iter < iter_limit:
        inputs = playlist_data.copy()
        inputs['videos'] = inputs['actual']
        outputs = playlist_data
        removals = playlist_data['corrections']['remove']
        logger.write("Beginning rearrangements of %s" % playlist_name)
        sequencer(inputs, outputs, removals, test=test)
        logger.write("Rearrangements complete", delim=True)
        playlist_data = verify_local_vs_youtube(playlist_data, playlist_name)
        diff = playlist_data['diff']
        for item in ['add', 'move', 'remove']:
            logger.write(len(playlist_data['corrections'][item]))
        iter += 1


def clean_backlog(primary_id, backlog_id, test=False):
    logger.write("Cleaning backlog", tier=1, header=True, delim=True)
    primary = YoutubePlaylist(id=primary_id, cache=cache, client=client)
    backlog = YoutubePlaylist(id=backlog_id, cache=cache, client=client)
    primary.get_playlist_items()
    backlog.get_playlist_items()
    backlog_list = create_video_list_from_playlist_items(backlog_id, backlog.title, backlog.videos)
    primary_list = create_video_list_from_playlist_items(primary_id, primary.title, primary.videos)

    remove_backlog_duplicates(primary_list=primary_list, backlog_list=backlog_list, test=test)
    logger.write("DONE cleaning backlog", tier=1, header=True)


def remove_shorts(playlist_handler, min_duration_sec=None, test=False):
    logger.write("Removing shorts from %s" % playlist_handler.title, tier=1, header=True, delim=True)
    min_duration = 0
    if not min_duration_sec:
        config_var = config.variables['VIDEO_MIN_DURATION']
        if 'DAYS' in config_var:
            min_duration += config_var['DAYS'] * 24 * 60 * 60
        if 'HOURS' in config_var:
            min_duration += config_var['HOURS'] * 60 * 60
        if 'MINUTES' in config_var:
            min_duration += config_var['MINUTES'] * 60
        if 'SECONDS' in config_var:
            min_duration += config_var['SECONDS']

    indexes = []
    index = 0
    for playlist_item in playlist_handler.videos:
        video = Video(id=playlist_item['contentDetails']['videoId'], cache=cache)
        if video.duration < min_duration or not video.data:
            video.remove_from_playlist(playlist_item_id=playlist_item['id'], test=test)
            indexes.append(index)
        index += 1

    for index in reversed(indexes):
        playlist_handler.videos.pop(index)

    cache.write_cache()
    logger.write("DONE removing shorts", tier=1, header=True, delim=True)


def remove_backlog_duplicates(primary_list, backlog_list, test=False):
    # duplicates = identify_duplicates(backlog_id, backlog_list)
    # remove_duplicates(duplicates, test)
    combined_list = primary_list + backlog_list
    duplicates = identify_duplicates(search_videos=combined_list)
    # for playlist_id in duplicates:
    #     vid_ids = duplicates[playlist_id]
    #     for vid_id in vid_ids:
    #         for instance in vid_ids[vid_id]:
    #             print(instance[0], instance[1]['title'])
    remove_duplicates(duplicates, test)


def subtract_b_videos_from_a(a_playlist, b_playlist, test=False):
    a_list = create_video_list_from_playlist_items(a_playlist.id, a_playlist.title, a_playlist.videos)
    b_list = create_video_list_from_playlist_items(b_playlist.id, b_playlist.title, b_playlist.videos)

    for b_vid in b_list:
        b_vid_id = b_vid['id']
        b_vid_item_id = b_vid['vid_source']['source_playlist_item_id']
        for a_vid in a_list:
            a_vid_id = a_vid['id']
            if a_vid_id == b_vid_id:
                video = Video(b_vid_id, cache=cache, client=client)
                video.remove_from_playlist(playlist_id=b_list.id, playlist_item_id=b_vid_item_id, test=test)


def create_video_list_from_playlist_items(playlist_id, playlist_name, playlist_items):
    video_list = []
    i = 0
    for video in playlist_items:
        entry = {
            "title": video['snippet']['title'],
            "url": "https://www.youtube.com/watch?v=%s" % video['contentDetails']['videoId'],
            "vid_id": video['contentDetails']['videoId'],
            "vid_source": {
                "source_playlist_id": playlist_id,
                "source_playlist_name": playlist_name,
                "source_playlist_position": i,
                "source_playlist_item_id": video['id']
            }
        }
        video_list.append(entry)
        i += 1

    return video_list


def import_queue(category='primary', test=False):
    playlists = [
        {
            "name": "primary",
            "id": ranks.data['playlist_ids'][category]
        },
        {
            "name": "queue",
            "id": ranks.data['queues'][category]
        },
        {
            "name": "backlog",
            "id": ranks.data['backlogs'][category]
        }
    ]
    playlist_map = {}
    for playlist in playlists:
        playlist_map[playlist['name']] = playlist['id']

    filler_tier = ranks.data['fillers'][category] if category in ranks.data['fillers'] else None

    fetched_playlists = fetch_playlists(playlist_map)

    for fetched_playlist_name in fetched_playlists:
        fetched_playlist = fetched_playlists[fetched_playlist_name]
        remove_shorts(fetched_playlist, test=test)

    result, overflow, remainder, queue_remainder = sort(playlist_map, fetched_playlists, category, filler_tier=filler_tier)
    cache.write_cache()
    assemble_local_playlists(
        primary_playlist_name=playlists[0]['name'],
        queue_name=playlists[1]['name'],
        backlog_name=playlists[2]['name'],
        playlist_map=playlist_map,
        result=result,
        backlog=overflow,
        remainder=remainder,
        queue_remainder=queue_remainder
    )
    cache.write_cache()
    logger.write("Playlists defined")

    verify(skip_wait=True)
    cache.write_cache()
    correct_playlists(playlists=playlists, test=test)
    cache.write_cache()
    logger.write()
    logger.write()
    cache.write_cache()
    clean_backlog(primary_id=playlist_map['primary'], backlog_id=playlist_map['backlog'])
    logger.write()

    logger.write("--------------------------------------------")
    logger.write("ORGANIZATION COMPLETE")
    logger.write("--------------------------------------------", delim=True)
