#!/usr/bin/env bash

DROPBOX_HOME=~/Dropbox
YOUTUBE_HOME=~/git/youtube-sorter
cd ${YOUTUBE_HOME}
source ${YOUTUBE_HOME}/python/bin/activate
for i in {1..59}; do
    if [[ ! -f ${YOUTUBE_HOME}/active ]]; then
        if [[ -f ${YOUTUBE_HOME}/import_queue ]] || [[ -f ${YOUTUBE_HOME}/import_queue.txt ]] || [[ -f ${DROPBOX_HOME}/import_queue ]] || [[ -f ${DROPBOX_HOME}/import_queue.txt ]]; then
            pushd ${YOUTUBE_HOME}
            touch ${YOUTUBE_HOME}/active
            python3 ${YOUTUBE_HOME}/import_all.py
            if [[ -f ${YOUTUBE_HOME}/import_queue ]]; then
                echo "Removing import_queue from YOUTUBE_HOME"
                rm ${YOUTUBE_HOME}/import_queue
            elif [[ -f ${YOUTUBE_HOME}/import_queue.txt ]]; then
                echo "Removing import_queue.txt from YOUTUBE_HOME"
                rm ${YOUTUBE_HOME}/import_queue.txt
            elif [[ -f ${DROPBOX_HOME}/import_queue ]]; then
                echo "Removing import_queue from DROPBOX_HOME"
                rm ${DROPBOX_HOME}/import_queue
            elif [[ -f ${DROPBOX_HOME}/import_queue.txt ]]; then
                echo "Removing import_queue.txt from DROPBOX_HOME"
                rm ${DROPBOX_HOME}/import_queue.txt
            fi
            if [[ -f ${DROPBOX_HOME}/sort_again ]]; then
                mv ${DROPBOX_HOME}/sort_again ${DROPBOX_HOME}/import_queue
            fi

            rm ${YOUTUBE_HOME}/active
            popd
        fi
    fi
    sleep 1
done
