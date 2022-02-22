from handlers.client import YoutubeClientHandler
from handlers.playlist import YoutubePlaylist, QueueHandler
from handlers.videos import Video
from handlers.ranks import RanksHandler
from handlers.cache import VideoCache
from handlers.utilities import Logger, ConfigHandler
import json
import datetime
import math


logger = Logger()
logger.write()
cache = VideoCache()
config = ConfigHandler()


def merge_lists(playlist_ids, tier_name, **kwargs):
    """

    @param tier_name:               The name of the tier as taken from ranks.json
    @param playlist_ids:            A list of IDs for each Youtube playlist that need to be merged
    @param kwargs:                  An catchall for any other kwargs that may be passed into the function
    @return:                        Returns the final sorted list of videos for the target playlist
    """

    logger.write("Initializing playlists")
    playlists = {}
    for playlist_id in playlist_ids:
        playlists[playlist_id] = YoutubePlaylist(id=playlist_id, cache=cache)

    logger.write("Getting playlist videos")
    playlist_videos = {}
    for playlist_id in playlists:
        playlist_videos[playlist_id] = get_playlist_videos(playlists[playlist_id], cache=cache)
    channel_list = get_tier_channels(tier_name)
    subscriptions = json.load(open("/Users/mjaranti/git/youtube-sorter/subscriptions.json", mode="r"))['details']

    logger.write()
    logger.write("Fetching channel subscriptions")
    channel_index = {}
    for channel_title in subscriptions:
        channel_info = subscriptions[channel_title]
        channel_id = channel_info['id']
        channel_index[channel_id] = channel_title

    logger.write()
    logger.write("Combining playlist videos")
    combined_unsorted = []
    for playlist_id in playlist_videos:
        combined_unsorted += playlist_videos[playlist_id]
    combined_unsorted = sort_by_date(combined_unsorted)

    # Sorts the channel IDs into a list
    logger.write("Sorting channel IDs")
    sorted_channel_ids = []
    for channel_name in channel_list:
        channel_id = subscriptions[channel_name]['id']
        sorted_channel_ids.append(channel_id)


    # Sorts the videos by their published date and then by their channel IDs
    channel_video_map = {}
    for video in combined_unsorted:
        channel_id = video.data['snippet']['channelId']
        if channel_id not in channel_video_map:
            channel_video_map[channel_id] = []
        channel_video_map[channel_id].append(video)

    # Creates a consolidated list of videos sorted by channel
    combined_sorted = []
    for channel_id in sorted_channel_ids:
        if channel_id in channel_video_map:
            for video in channel_video_map[channel_id]:
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


def check_validity(video):
    """
    Checks the validity of a given Video() object based on the criteria specified in config.json

    @param video:   A Video() object
    @return:        True or False
    """

    min_duration_sec = convert_to_seconds(config.variables['VIDEO_MIN_DURATION'])
    max_duration_sec = convert_to_seconds(config.variables['VIDEO_MAX_DURATION'])

    video = Video(id="test")
    if not video.private:
        duration = video.data['contentDetails']['duration'].replace("P", "").replace("T", "")
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


def sort_by_date(video_list):
    """
    @param video_list:  An unsorted list of Video() objects
    @return:            A list of Video() objects sorted by date published
    """
    logger.write("Sorting by date")
    date_map = {}
    for video in video_list:
        published_date = datetime.datetime.strptime(video.data['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
        date_map[published_date] = video

    sorted_list = []
    for published_date in date_map:
        sorted_list.append(date_map[published_date])

    return sorted_list


def get_playlist_videos(playlist_handler):
    """

    @param playlist_handler:    The YoutubePlaylist() object for the playlist to get the videos of
    @return:                    Returns a list of Video() objects presumably ordered by their positions in the playlist
    """

    playlist_handler.get_playlist_items()

    playlist_videos = []
    for playlist_item in playlist_handler.videos:
        vid_id = playlist_item['contentDetails']['videoId']
        vid_kwarg = {
            'id': vid_id,
            'cache': cache
        }
        video = Video(**vid_kwarg)
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


def calculate_overflow(original_playlist, max_len, min_len, max_fill=10, backlog="backlog"):
    """
    Calculates how many videos to send to the overflow playlist

    @param original_playlist:   The playlist to calculate overflow for
    @param max_len:             The maximum length that the playlist can be before overflow videos are removed
    @param min_len:             The minimum length that the playlist can be before filler videos are added
    @param max_fill:            The maximum number of filler videos to add to the original playlist
    @param backlog:             The destination of the overflowed videos and the source for the filler videos
    @return:
    """

    primary = []
    overflow = []

    if len(original_playlist) > max_len:
        primary = original_playlist[:max_len]
        overflow = original_playlist[max_len:]
    elif len(original_playlist) < min_len:
        primary += add_filler(original_playlist, cache, min_len, max_fill, backlog)

    return primary, overflow


def add_filler(combined_playlist, vid_cache, min_len, max_fill=10, filler_source_name="backlog"):
    ranks = RanksHandler()
    filler_source_id = ranks.data['playlist_ids'][filler_source_name]
    filler_source = YoutubePlaylist(id=filler_source_id, cache=vid_cache)
    filler_source.get_playlist_items()
    filler_list = []
    filler_to_add = min_len - len(combined_playlist)

    added = 0
    while added < filler_to_add and added < max_fill:
        filler_list.append(filler_source.videos[added])
        added += 1

    return filler_list


queue = QueueHandler(cache=cache)
max_length = config.variables['AUTOLIST_MAX_LENGTH']
min_length = math.ceil(max_length/2)
max_filler = config.variables['FILLER_LENGTH']

combined = merge_lists(
    playlist_ids=[
        'PL8wvcc8NSIHL0D2-YkHcojXU5e6w1YxJm',
        queue.id,
        'PL8wvcc8NSIHIHFbnOfyXxHo2Q3UnlSpa4'
    ],
    tier='primary',
    cache=cache
)

result, overflow = calculate_overflow(combined, max_len=max_length, min_len=min_length, max_fill=max_filler, backlog="backlog")

print(len(result))
for video in result:
    print("\t%s: %s" % (video.data['snippet']['channelTitle'], video.title))

print()
print(len(overflow))
for video in overflow:
    print("\t%s: %s" % (video.data['snippet']['channelTitle'], video.title))

