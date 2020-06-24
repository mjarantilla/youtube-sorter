import os
import os.path
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google_auth_oauthlib import flow
from handlers.utilities import ConfigHandler, print_json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class YoutubeClientHandler:
    def __init__(self, pickle=None, secrets_filepath=None, clear=False):
        self.pickle = "token.pickle" if pickle is None else pickle
        if clear:
            if os.path.exists(self.pickle):
                os.remove(self.pickle)

        self.config = ConfigHandler()
        self.secrets_filepath = self.config.secrets_filepath if secrets_filepath is None else secrets_filepath
        self.client = self.get_client()

        print(self.pickle)
        print(self.secrets_filepath)

    def refresh_vars(self):
        self.config = ConfigHandler()

    def get_client(self):
        scopes = self.config.variables['SCOPES']
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = self.config.variables['API_SERVICE_NAME']
        api_version = self.config.variables['API_VERSION']
        client_secrets_file = self.secrets_filepath

        # Get credentials and create an API client
        # flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        #     client_secrets_file, scopes)
        # credentials = flow.run_console()
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.pickle):
            with open(self.pickle, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.pickle, 'wb') as token:
                pickle.dump(creds, token)

        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=creds)

        return youtube

    def execute(self, request_object):
        response = request_object.execute()

        return response