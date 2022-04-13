from handlers.utilities import ConfigHandler, print_json, Logger
from handlers.client import YoutubeClientHandler
import json
import os
import shutil


def remove_duplicates(private_videos):
    tmp_list = []
    for vid_id in private_videos:
        if vid_id not in tmp_list:
            tmp_list.append(vid_id)

    return tmp_list


def is_private(vid_id):
    client_handler = YoutubeClientHandler()
    request = client_handler.client.videos().list(
        part="contentDetails,id,snippet",
        id=vid_id
    )
    response = client_handler.execute(request)
    if len(response['items']) == 0:
        return True
    else:
        for item in response['items']:
            logger.write("%s: %s - %s" % (vid_id, item['snippet']['channelTitle'], item['snippet']['title']))
        return False

logger = Logger()
config = ConfigHandler()
private_videos_file = config.variables['PRIVATE_VIDEOS_FILE']
tmp_file = private_videos_file+".tmp"
shutil.copy(private_videos_file, tmp_file)
private_fp = open(private_videos_file, mode='r')
newfile_fp = open(tmp_file, mode='w')
private_vids_data = json.load(private_fp)
private_videos = private_vids_data['private_videos']
deduped_videos = remove_duplicates(private_videos)

newlist = []
unprivate = []
for vid_id in deduped_videos:
    if is_private(vid_id)[0]:
        newlist.append(vid_id)
    else:
        unprivate.append(vid_id)

private_vids_data['private_videos'] = newlist
unprivated_videos = private_videos_file+".unprivated"
unprivated_videos_fp = open(unprivated_videos, mode='w')
print_json(private_vids_data, newfile_fp)
print_json(unprivate, unprivated_videos_fp)
shutil.move(private_videos_file, private_videos_file+".bk")
shutil.move(tmp_file, private_videos_file)