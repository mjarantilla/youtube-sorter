from handlers.client import YoutubeClientHandler
from handlers.playlist import YoutubePlaylist, QueueHandler
from handlers.videos import Video
from handlers.ranks import RanksHandler
from handlers.cache import VideoCache
from handlers.utilities import Logger, ConfigHandler
import json
import datetime


logger = Logger()
logger.write()
cache = VideoCache()


def merge_lists(playlist_ids, tier, **kwargs):
    """

    @param queue_videos:            A list of vid_data dictionaries for all the videos on the queue to be imported
    @param target_playlist_videos:  A list of vid_data dictionaries for all the videos on the playlist that the queue
                                    will be imported into
    @param channel_list:            The sorted list of channel names for the target playlist taken from ranks.json
    @param subscriptions:           The list of current channel subscriptions and their YouTube channel IDs
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
    # private_videos_file = kwargs['private_videos_file']
    channel_list = get_tier_channels(tier)
    subscriptions = json.load(open("/Users/mjaranti/git/youtube-sorter/subscriptions.json", mode="r"))['details']

    logger.write()
    logger.write("Fetching channel subscriptions")
    channel_index = {}
    for channel_title in subscriptions:
        channel_info = subscriptions[channel_title]
        channel_id = channel_info['id']
        channel_index[channel_id] = channel_title

    # Load data about videos marked "private" on YouTube
    # private_fp = open(private_videos_file, mode='r')
    # private_vids_data = json.load(private_fp)
    # private_videos = private_vids_data['private_videos']
    # private_fp.close()
    # private_fp = open(private_videos_file, mode='w')
    # json.dump({'private_videos': private_videos}, fp=private_fp, separators=(',', ': '), indent=2, sort_keys=True)
    # private_fp.close()

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


def sort_by_date(video_list):
    logger.write("Sorting by date")
    date_map = {}
    for video in video_list:
        published_date = datetime.datetime.strptime(video.data['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
        date_map[published_date] = video

    sorted_list = []
    for published_date in date_map:
        sorted_list.append(date_map[published_date])

    return sorted_list


def get_playlist_videos(playlist_handler, **kwargs):
    playlist_handler.get_playlist_items()

    playlist_videos = []
    for playlist_item in playlist_handler.videos:
        vid_id = playlist_item['contentDetails']['videoId']
        vid_kwarg = {
            'id': vid_id
        }
        if 'cache' in kwargs:
            vid_kwarg['cache'] = kwargs['cache']
        video = Video(**vid_kwarg)
        playlist_videos.append(video)

    return playlist_videos


def get_tier_channels(tier_name):
    handler = RanksHandler()
    handler.define_ranks()

    specified_tier = None
    for tier in handler.rank_data:
        if tier.name == tier_name:
            specified_tier = tier

    channels = specified_tier.get_channels()

    return channels


def calculate_overflow(combined, max_length, min_length, max_filler=10, filler_source="backlog"):
    primary = []
    overflow = []

    if len(combined) > max_length:
        primary = combined[:max_length]
        overflow = combined[max_length:]
    elif len(combined) < min_length:
        primary += add_filler(combined, cache, min_length, max_filler, filler_source)

    return primary, overflow


def add_filler(combined, cache, min_length, max_filler=10, filler_source_name="backlog"):
    ranks = RanksHandler()
    filler_source_id = ranks.data['playlist_ids'][filler_source_name]
    filler_source = YoutubePlaylist(id=filler_source_id, cache=cache)
    filler_source.get_playlist_items()
    filler_list = []
    filler_to_add = min_length - len(combined)

    added = 0
    while added < filler_to_add and added < max_filler:
        filler_list.append(filler_source.videos[added])
        added += 1

    return filler_list


queue = QueueHandler(cache=cache)
result = merge_lists(
    playlist_ids=[
        'PL8wvcc8NSIHL0D2-YkHcojXU5e6w1YxJm',
        queue.id,
        'PL8wvcc8NSIHIHFbnOfyXxHo2Q3UnlSpa4'
    ],
    tier='primary',
    cache=cache
)

print(len(result))
for video in result:
    print("\t%s: %s" % (video.data['snippet']['channelTitle'], video.title))
