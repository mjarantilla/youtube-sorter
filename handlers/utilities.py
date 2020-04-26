from datetime import datetime
import json
import shutil
import os
from os import path


class ConfigHandler:
    def __init__(self, cwd=None, config_file="config.json"):
        self.home = os.getcwd() if cwd is None else cwd
        self.variables = None
        self.config_file = os.path.join(self.home, config_file)
        self.read_config_file(self.config_file)
        self.current_date = datetime.now().strftime(self.variables['DATE_FORMAT'])

        # Paths and directories
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

    def print_config_file(self):
        print_json(self.variables)


class Logger:
    def __init__(self, silent=False):
        self.config = ConfigHandler()
        self.silent = silent
        self.file = self.config.log_filepath
        self.format = self.config.variables['YOUTUBE_DATE_FORMAT']

    def initialize(self):
        fp = open(self.file, mode='w')
        fp.close()
        message = LogMessage(
            msg="Starting new logfile",
            event_time_format=self.format,
            logfile=self.file,
            silent=self.silent
        )
        message.write()

    def rename(self):
        log_date = datetime.now()
        file_suffix_format = self.config.variables['LOG_DATE_FORMAT']
        file_suffix = log_date.strftime(file_suffix_format)
        if log_date.hour == 0 and log_date.minute == 0 and log_date.second == 0:
            shutil.copyfile(self.file, ".".join([self.file,file_suffix]))
            self.initialize()

    def write(self, msg):
        self.rename()
        message = LogMessage(
            msg=msg,
            event_time_format=self.format,
            logfile=self.file,
            silent=self.silent
        )
        message.write()


class LogMessage:
    def __init__(self, msg, event_time_format, logfile, silent=False):
        self.date = datetime.now()
        self.event_time = self.date.strftime(event_time_format)
        self.msg = msg
        self.logfile = logfile
        self.silent = silent

    def write(self):
        fp = open(self.logfile, mode='a')
        print(": ".join([self.event_time, self.msg]), file=fp)
        fp.close()

        if not self.silent:
            print(": ".join([self.event_time, self.msg]))


def print_json(obj, fp=None):
    import json

    if fp is None:
        print(json.dumps(obj, separators=(',', ': '), indent=2, sort_keys=True))
    else:
        print(json.dumps(obj, separators=(',', ': '), indent=2, sort_keys=True), file=fp)


def log(msg, silent=False):
    try:
        config = ConfigHandler()
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