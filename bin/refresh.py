from handlers.utilities import print_json, ConfigHandler
from handlers.playlist import QueueHandler
import os


def queue():
    queue = QueueHandler()
    config = ConfigHandler()

    cache_dir = config.variables['CACHE_DIR']
    queue_json = os.path.join(cache_dir, "queue.json")
    queue_json_fp = open(queue_json, mode='w')

    queue.get_playlist_items()
    queue.update_video_cache()