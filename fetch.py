#!/usr/local/bin/python3.6
from handlers.playlist import QueueHandler, LegacyRecords


def merge():
    records = LegacyRecords()
    records.combine_data()
    records.write_records()

merge()
queue = QueueHandler()
queue.scan_all_channels()