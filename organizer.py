from handlers.client import YoutubeClientHandler
import json


def import_queue(queue_videos, target_playlist_videos, channel_list, subscriptions, **kwargs):
    """

    @param queue_videos:            A list of vid_data dictionaries for all the videos on the queue to be imported
    @param target_playlist_videos:  A list of vid_data dictionaries for all the videos on the playlist that the queue
                                    will be imported into
    @param channel_list:            The sorted list of channels for the target playlist
    @param subscriptions:           The list of current channel subscriptions and their YouTube channel IDs
    @param kwargs:                  An catchall for any other kwargs that may be passed into the function
    @return:                        Returns the final sorted list of videos for the target playlist
    """

    queue_videos = queue_videos
    target_playlist = target_playlist_videos
    private_videos_file = kwargs['private_videos_file']
    channel_list = channel_list
    subscriptions = subscriptions

    channel_index = {}
    for channel_title in subscriptions:
        channel_info = subscriptions[channel_title]
        channel_id = channel_info['id']
        channel_uploads = channel_info['uploads']
        channel_index[channel_id] = channel_title

    # Load data about videos marked "private" on YouTube
    private_fp = open(private_videos_file, mode='r')
    private_vids_data = json.load(private_fp)
    private_videos = private_vids_data['private_videos']
    private_fp.close()
    private_fp = open(private_videos_file, mode='w')
    json.dump({'private_videos': private_videos}, fp=private_fp, separators=(',', ': '), indent=2, sort_keys=True)
    private_fp.close()

    client_handler = YoutubeClientHandler()
    client = client_handler.client

    combined_playlist = queue_videos + target_playlist
