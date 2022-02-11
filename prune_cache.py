from handlers.cache import VideoCache
from handlers.ranks import RanksHandler
from handlers.playlist import YoutubePlaylist
from handlers.utilities import print_json

ranks = RanksHandler()
ranks.define_ranks()
playlist_ids = ranks.data['playlist_ids']

cache = VideoCache()
for playlist_id in playlist_ids:
    playlist = YoutubePlaylist(id=playlist_id, cache=cache)
    playlist.sync_local_with_yt()

