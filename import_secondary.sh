#!/usr/bin/env bash

YOUTUBE_HOME=~/git/youtube-sorter
pushd ${YOUTUBE_HOME} || exit
source python/bin/activate
python3 import_secondary.py
popd || exit
