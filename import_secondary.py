#!/usr/bin/env python3

from bin import organizer


def main(test=False):
    organizer.import_queue(category="backlog", test=test, max_length=100, date_sorting=True)


main()