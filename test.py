from handlers import utilities, client, playlist, ranks
kwargs = {
    'playlist_id': 'UUiDJtJKMICpb9B1qf7qjEOA',
    'channel_id': 'UCiDJtJKMICpb9B1qf7qjEOA'
}
test_playlist = playlist.SubscribedChannel(**kwargs)
response = test_playlist.get_latest()
for item in response['items']:
    utilities.print_json(item)
# input()
# for item in response['items']:
#     print(item['snippet']['position'], item['snippet']['title'], item['snippet']['publishedAt'], sep="\t")