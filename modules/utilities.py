from datetime import datetime
import json
import shutil
import os
from os import path


class ConfigVariables:
    def __init__(self, config_file="config.json"):
        self.variables = None
        self.config_file = config_file
        self.read_config_file(config_file)
        self.current_date = datetime.now().strftime(self.variables['DATE_FORMAT'])

        # Paths and directories
        self.home = os.getcwd()
        self.log_path = path.join(self.home, 'logs')
        self.secrets_filepath = path.join(self.home, self.variables['CLIENT_SECRETS_FILE'])
        self.records_filepath = path.join(self.home, self.variables['RECORDS_FILE'])
        self.ranks_filepath = path.join(self.home, self.variables['RANKS_FILE'])
        self.subscriptions_filepath = path.join(self.home, self.variables['SUBSCRIPTIONS_FILE'])
        self.private_videos_filepath = path.join(self.home, self.variables['PRIVATE_VIDEOS_FILE'])
        self.log_filepath = path.join(self.log_path, 'current.log')

    def read_config_file(self, config_file=None):
        if config_file is None:
            config_file = self.config_file

        config_fp = open(config_file)
        self.variables = json.load(config_fp)
        config_fp.close()


def print_json(obj, fp=None):
    import json

    if fp is None:
        print(json.dumps(obj, separators=(',', ': '), indent=2, sort_keys=True))
    else:
        print(json.dumps(obj, separators=(',', ': '), indent=2, sort_keys=True), file=fp)


def log(msg, silent=False):
    try:
        config = ConfigVariables()
        log_date_format = config.variables['LOG_DATE_FORMAT']
        log_file = config.variables['LOG_FILE']
        log_date = datetime.now()
        log_date_formatted = log_date.strftime(log_date_format)
        renamed = False
        if log_date.hour == 0 and log_date.minute == 0 and log_date.second == 0:
            print("Renaming log file")
            log_msg = ': '.join(
                [
                    str(log_date_formatted),
                    "Renaming log file"
                ]
            )
            shutil.copyfile(log_file, log_file + "." + datetime.now().strftime(log_date_format))
            renamed = True

        if renamed:
            log_fp = open(log_file, mode='w')
            print("Renamed log file", file=log_fp)
        else:
            log_fp = open(log_file, mode='a')
        log_msg = ': '.join(
            [
                str(log_date_formatted),
                msg
            ]
        )

        print(log_msg, file=log_fp)
        if not silent:
            print(log_msg)
        log_fp.close()
    except:
        print_json(msg)
        raise

