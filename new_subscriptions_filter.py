#!/usr/bin/python

import httplib2

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

# playing around. with youtube api.
# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
# DEVELOPER_KEY = "AIzaSyDKReTaQ4FK4i3CY8jjcYe8izEfJybYlss"

CHANNEL_ID = "UCRrN04dF5AkuOng2kh23ptg"
CREDENTIAL_FILE = "client_secrets.json"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def get_authenticated_service():
    # def get_authenticated_service(args):
    flow = flow_from_clientsecrets(
        # filename=args.secrets,
        filename=CREDENTIAL_FILE,
        message=(
            "Missing client_secrets.json file.\nDownload from "
            "https://console.developers.google.com"
            "/project/YOUR_PROJECT_ID/apiui/credential."
        ),
        scope="https://www.googleapis.com/auth/youtube",
    )
    storage = Storage(".channel_to_playlist-oauth2-credentials.json")
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, None)

    fiddler_proxy_traffic_testing = False  # if true set env variable: set HTTPS_PROXY=http://127.0.0.1:8888
    http = httplib2.Http(disable_ssl_certificate_validation=fiddler_proxy_traffic_testing)
    return build("youtube", "v3", http=credentials.authorize(http))


def get_videos():
    # youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    youtube = get_authenticated_service()

    print("Fetching Subscription list")
    all_subscriptions = get_subscriptions(youtube, CHANNEL_ID)
    # print(all_subscriptions)
    # for subscription in all_subscriptions:
    #     print(subscription['snippet']['title'])

    print("Total subscriptions: %s" % len(all_subscriptions))
    videos = []
    for subscription in all_subscriptions:
        channel_id = subscription['snippet']['resourceId']['channelId']
        print("Getting Upload-Playlist-ID for %s" % subscription['snippet']['title'])
        playlist_id = get_channel_upload_playlist_id(youtube, channel_id)  # to this point quota +7
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=5
        ).execute()  # quota +12
        print(playlist_response)

        item = playlist_response['items'][0]
        video_id = item['snippet']['resourceId']['videoId']
        video_response = youtube.videos().list(
            part="snippet,contentDetails,statistics",  #
            id=video_id).execute()
        print(video_response)

        exit(0)
        for playlist_item in playlist_response['items']:
            videos.append({
                "id": playlist_item['snippet']['resourceId']['videoId'],
                "title": playlist_item['snippet']['title'],
                "description": playlist_item['snippet']['description'],
                "date": playlist_item['snippet']['publishedAt'],
                "channel": playlist_item['snippet']['channelTitle'],
            })

        print(len(videos))

    videos_sorted = sorted(videos, key=lambda k: k['date'], reverse=True)

    return videos_sorted


def get_subscriptions(youtube, channel_id):
    all_subscriptions = []
    subscriptions_list_request = youtube.subscriptions().list(
        part="snippet",
        channelId=channel_id,
        maxResults=50,
    )
    while subscriptions_list_request:
        subscriptions_list_response = subscriptions_list_request.execute()
        for subscriptions_list_item in subscriptions_list_response['items']:
            all_subscriptions.append(subscriptions_list_item)
        subscriptions_list_request = youtube.subscriptions().list_next(subscriptions_list_request,
                                                                       subscriptions_list_response)
    return all_subscriptions


def get_channel_upload_playlist_id(youtube, channel_id):
    channel_response = youtube.channels().list(id=channel_id, part="contentDetails").execute()
    return channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def main():
    for video in get_videos():
        print(video['id'])


if __name__ == "__main__":
    main()
