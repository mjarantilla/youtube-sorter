#!/usr/bin/env python3

from bin import organizer


def main(test=False):
    organizer.import_queue(category="primary", test=test)
    organizer.import_queue(category="f1", test=test)


main()
