#!/usr/bin/env bash

DROPBOX_HOME=~/Dropbox/
YOUTUBE_HOME=${DROPBOX_HOME}/Apps/youtube-sorter/
for i in {1..59}; do
    if [[ ! -f ${YOUTUBE_HOME}/active ]]; then
        if [[ -f ${YOUTUBE_HOME}/check ]] || [[ -f ${YOUTUBE_HOME}/check.txt ]] || [[ -f ${DROPBOX_HOME}/check ]] || [[ -f ${DROPBOX_HOME}/check.txt ]]; then
            pushd ${YOUTUBE_HOME}
            touch ${YOUTUBE_HOME}/active
            python/bin/python fetch.py
            if [[ -f ${YOUTUBE_HOME}/check ]]; then
                echo "Removing check from YOUTUBE_HOME"
                rm ${YOUTUBE_HOME}/check
            elif [[ -f ${YOUTUBE_HOME}/check.txt ]]; then
                echo "Removing check.txt from YOUTUBE_HOME"
                rm ${YOUTUBE_HOME}/check.txt
            elif [[ -f ${DROPBOX_HOME}/check ]]; then
                echo "Removing check from DROPBOX_HOME"
                rm ${DROPBOX_HOME}/check
            elif [[ -f ${DROPBOX_HOME}/check.txt ]]; then
                echo "Removing check.txt from DROPBOX_HOME"
                rm ${DROPBOX_HOME}/check.txt
            fi
            rm ${YOUTUBE_HOME}/active
            popd
        fi
    fi
    sleep 1
done
