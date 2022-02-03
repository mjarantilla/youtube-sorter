#!/usr/bin/env bash

DROPBOX_HOME=~/Dropbox/
YOUTUBE_HOME=~/git/youtube-sorter
source python/bin/activate
for i in {1..59}; do
    if [[ ! -f ${YOUTUBE_HOME}/active ]]; then
        if [[ -f ${YOUTUBE_HOME}/refresh_channels ]] || [[ -f ${YOUTUBE_HOME}/refresh_channels.txt ]] || [[ -f ${DROPBOX_HOME}/refresh_channels ]] || [[ -f ${DROPBOX_HOME}/refresh_channels.txt ]]; then
            pushd ${YOUTUBE_HOME}
            touch ${YOUTUBE_HOME}/active
            python3 refresh_channels.py
            if [[ -f ${YOUTUBE_HOME}/refresh_channels ]]; then
                echo "Removing refresh_channels from YOUTUBE_HOME"
                rm ${YOUTUBE_HOME}/refresh_channels
            elif [[ -f ${YOUTUBE_HOME}/refresh_channels.txt ]]; then
                echo "Removing refresh_channels.txt from YOUTUBE_HOME"
                rm ${YOUTUBE_HOME}/refresh_channels.txt
            elif [[ -f ${DROPBOX_HOME}/refresh_channels ]]; then
                echo "Removing refresh_channels from DROPBOX_HOME"
                rm ${DROPBOX_HOME}/refresh_channels
            elif [[ -f ${DROPBOX_HOME}/refresh_channels.txt ]]; then
                echo "Removing refresh_channels.txt from DROPBOX_HOME"
                rm ${DROPBOX_HOME}/refresh_channels.txt
            fi
            rm ${YOUTUBE_HOME}/active
            popd
        fi
    fi
    sleep 1
done
