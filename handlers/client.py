import os
import os.path
import pickle
import time
import googleapiclient.discovery
import googleapiclient.errors
from google_auth_oauthlib import flow
from handlers.utilities import ConfigHandler, print_json, Logger
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logger = Logger(tier=5)


class YoutubeClientHandler:
    def __init__(self, pickle=None, secrets_filepath=None, clear=False):
        self.pickle = "token.pickle" if pickle is None else pickle
        if clear:
            if os.path.exists(self.pickle):
                os.remove(self.pickle)

        self.config = ConfigHandler()
        self.secrets_filepath = self.config.secrets_filepath if secrets_filepath is None else secrets_filepath
        self.client = self.get_client()

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
        logger.write("Querying Youtube: %s %s" % (request_object.method, request_object.methodId))
        try:
            response = request_object.execute()
        except googleapiclient.errors.HttpError as err:
            response = err.resp
            logger.write("Response:")
            logger.write(response)
            logger.write()
            logger.write("Content")
            logger.write(err.content)
            logger.write()
            logger.write("Error Details")
            logger.write(err.error_details)
            raise

        return response

    def build_resource(self, properties):
        resource = {}
        for p in properties:
            # Given a key like "snippet.title", split into "snippet" and "title", where
            # "snippet" will be an object and "title" will be a property in that object.
            prop_array = p.split('.')
            ref = resource
            for pa in range(0, len(prop_array)):
                is_array = False
                key = prop_array[pa]

                # For properties that have array values, convert a name like
                # "snippet.tags[]" to snippet.tags, and set a flag to handle
                # the value as an array.
                if key[-2:] == '[]':
                    key = key[0:len(key) - 2:]
                    is_array = True

                if pa == (len(prop_array) - 1):
                    # Leave properties without values out of inserted resource.
                    if properties[p]:
                        if is_array:
                            ref[key] = properties[p].split(',')
                        else:
                            ref[key] = properties[p]
                elif key not in ref:
                    # For example, the property is "snippet.title", but the resource does
                    # not yet have a "snippet" object. Create the snippet object here.
                    # Setting "ref = ref[key]" means that in the next time through the
                    # "for pa in range ..." loop, we will be setting a property in the
                    # resource's "snippet" object.
                    ref[key] = {}
                    ref = ref[key]
                else:
                    # For example, the property is "snippet.description", and the resource
                    # already has a "snippet" object.
                    ref = ref[key]
        return resource

    def playlist_items_insert(self, properties, **kwargs):
        # See full sample for function
        resource = self.build_resource(properties)

        # See full sample for function
        kwargs = self.remove_empty_kwargs(**kwargs)
        request = self.client.playlistItems().insert(body=resource, **kwargs)
        response = self.execute(request)

        return response

    def playlist_item_update_position(self, properties, **kwargs):
        # See full sample for function
        resource = self.build_resource(properties)

        # See full sample for function
        kwargs = self.remove_empty_kwargs(**kwargs)
        request = self.client.playlistItems().update(body=resource, **kwargs)
        response = self.execute(request)

        return response

    def remove_empty_kwargs(self, **kwargs):
        good_kwargs = {}
        if kwargs is not None:
            for key, value in kwargs.items():
                if value:
                    good_kwargs[key] = value
        return good_kwargs
