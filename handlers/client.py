import os
import os.path
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from handlers.utilities import ConfigHandler
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class YoutubeClientHandler:
    def __init__(self):
        self.config = ConfigHandler()
        self.client = self.get_client()

    def refresh_vars(self):
        self.config = ConfigHandler()

    def get_client(self):
        scopes = self.config.variables['SCOPES']
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = self.config.secrets_filepath

        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        # credentials = flow.run_console()
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
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
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=creds)

        return youtube