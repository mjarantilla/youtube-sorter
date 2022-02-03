#!/bin/bash

pushd ~/git/youtube-sorter
mv ./token.pickle ./token.pickle.main
mv ./token.pickle.all ./token.pickle
source ./python/bin/activate
python3 ./fetch.py -a
mv ./token.pickle ./token.pickle.all
mv ./token.pickle.main ./token.pickle
