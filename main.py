from handlers import client, playlist, ranks, utilities
import argparse

def main():
    args = {}
    flags = {}
    parser = argparse.ArgumentParser(description='Process some integers.')

    args = parser.parse_args()
    print(args.accumulate(args.integers))
