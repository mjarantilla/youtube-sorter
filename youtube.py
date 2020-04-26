from handlers import client


def main():
    handler = client.YoutubeClientHandler()

    request = handler.client.channels().list(
        part="snippet,contentDetails,statistics",
        id="UC_x5XG1OV2P6uZZ5FSM9Ttw"
    )
    response = request.execute()

    print(response)

    return None


if __name__ == "__main__":
    main()