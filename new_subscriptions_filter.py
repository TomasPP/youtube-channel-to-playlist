#!/usr/bin/python

import json
import os
import sys
import warnings
import requests
from http import HTTPStatus

import util
import dateutil.parser
import httplib2
from apiclient.discovery import build
from apiclient.errors import HttpError
from dateutil import tz
from jsonpath_ng import parse
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

# playing around. with youtube api.
# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
# DEVELOPER_KEY = "...."

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


def test1():
    for video in get_videos():
        print(video['id'])


class VideoInfo:
    video_id = None
    percent_watched = 0

    def __init__(self, video_id, percent_watched=0):
        self.video_id = video_id
        self.percent_watched = percent_watched


class VideoInfoList:
    videos = {}

    def update_info(self, video_id, percent_watched):
        info = self.videos[video_id]
        info.percent_watched = percent_watched

    def get_unfinished_ids(self):
        result = []
        for video_id in self.videos.keys():
            percent = self.videos[video_id].percent_watched
            if percent < 95:
                result.append(video_id)
                # if percent == 0:
                #     print(video_id)
        return result

    def is_empty(self):
        return len(self.videos) == 0


def get_unfinished_videos(json_str):
    result = VideoInfoList()
    # with open(json_file_name, encoding="utf8") as json_file:
    data = json.loads(json_str)

    video_matches = parse('$..gridVideoRenderer.videoId').find(data)
    if len(video_matches) == 0:
        return result
    for video_match in video_matches:
        video_id = video_match.value
        result.videos[video_id] = VideoInfo(video_id)
    # print("json videos len", len(video_matches))

    jpe = parse('`parent`.`parent`.`parent`.`parent`.videoId')
    percent_matches = parse('$..percentDurationWatched').find(data)
    for percent_match in percent_matches:
        percent_watched = percent_match.value
        video_id_matches = jpe.find(percent_match)
        video_id = video_id_matches[0].value

        result.update_info(video_id, percent_watched)

    # print('percent_match len', len(percent_matches))
    return result


def _parse_date(string):
    dt = dateutil.parser.parse(string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.UTC)
    return dt


def get_playlist_video_ids(
    youtube, playlist_id, *, published_after=None, published_before=None, http=None
):
    request = youtube.playlistItems().list(playlistId=playlist_id, part="snippet", maxResults=50)
    items = []
    while request:
        response = request.execute(http=http)
        items += response["items"]
        request = youtube.playlistItems().list_next(request, response)
    if published_after is not None:
        items = [
            item
            for item in items
            if _parse_date(item["snippet"]["publishedAt"]) >= published_after
        ]
    if published_before is not None:
        items = [
            item
            for item in items
            if _parse_date(item["snippet"]["publishedAt"]) < published_before
        ]
    items.sort(key=lambda item: _parse_date(item["snippet"]["publishedAt"]))
    return [item["snippet"]["resourceId"]["videoId"] for item in items]


def add_video_to_playlist(youtube, playlist_id, video_id, position=None):
    try:
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"videoId": video_id, "kind": "youtube#video"},
            }
        }
        if position is not None:
            body["snippet"]["position"] = position

        youtube.playlistItems().insert(
            part="snippet",
            body=body,
        ).execute()
    except HttpError as exc:
        if exc.resp.status == HTTPStatus.CONFLICT:
            # watch-later playlist don't allow duplicates
            raise VideoAlreadyInPlaylistError()
        raise


class VideoAlreadyInPlaylistError(Exception):
    """ video already in playlist """


def add_to_playlist(youtube, playlist_id, video_ids, added_videos_file, add_duplicates):
    added_videos = []
    existing_videos = get_playlist_video_ids(youtube, playlist_id)
    count = len(video_ids)
    for video_num, video_id in enumerate(video_ids, start=1):
        if video_id in existing_videos and not add_duplicates:
            continue
        sys.stdout.write("\rAdding video {} of {}".format(video_num, count))
        sys.stdout.flush()
        try:
            # adding videos in reverse order always at position 0
            add_video_to_playlist(youtube, playlist_id, video_id, 0)
            added_videos.append(video_id)
        except VideoAlreadyInPlaylistError:
            if add_duplicates:
                warnings.warn(f"video {video_id} cannot be added as it is already in the playlist")
        if added_videos_file:
            added_videos_file.write(video_id + "\n")
        existing_videos.append(video_id)
    if count:
        sys.stdout.write("\n")
    print("added video count", len(added_videos))


def extract_json(html):
    pos = html.find('percentDurationWatched')
    start_script_tag_pos = html.rfind('<script', 0, pos)
    end_script_tag_pos = html.find('</script', pos)
    start_bracket_pos = html.find('{', start_script_tag_pos)
    end_bracket_pos = html.rfind('}}}', start_bracket_pos, end_script_tag_pos)
    json_str = html[start_bracket_pos:end_bracket_pos + 3]
    return json_str


def get_ytube_html():
    cookie_file = 'cookies.txt'
    url = 'https://www.youtube.com/feed/subscriptions'
    agent_header = 'User-Agent'
    agent_value = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
    headers = {agent_header: agent_value}
    cookie_jar = util.YoutubeDLCookieJar(cookie_file)
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    # self.cookiejar.save(ignore_discard=True, ignore_expires=True)
    response = requests.get(url, cookies=cookie_jar, headers=headers)  # verify=False
    text = response.text
    return text


def read_file_into_str(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf8') as file:
            return file.read()


def write_str_to_file(file_name, text):
    with open(file_name, 'w', encoding='utf8') as file:
        file.write(text)
        file.close()


def test2():
    html_file_name = 'youtube.html'
    json_file_name = 'youtube.json'
    html = read_file_into_str(html_file_name)
    if html is None:
        html = get_ytube_html()

    write_str_to_file(html_file_name, html)

    json_str = extract_json(html)
    write_str_to_file(json_file_name, json_str)

    # json_file_name = 'youtube.json'
    playlist_id = 'PLTgIihucics9gK7wE_AcgUCXipPMARoiJ'
    allow_duplicates = False
    result = get_unfinished_videos(json_str)
    if result.is_empty():
        print('ERROR: html contains no videos.')
        return
    video_ids = result.get_unfinished_ids()
    video_ids.reverse()

    print('videos to add', len(video_ids))
    # print(video_ids)
    youtube = get_authenticated_service()
    added_videos_filename = "playlist-{}-added-videos".format(playlist_id)

    if os.path.exists(added_videos_filename):
        with open(added_videos_filename) as f:
            added_video_ids = set(map(str.strip, f.readlines()))
        video_ids = [vid_id for vid_id in video_ids if vid_id not in added_video_ids]

    with open(added_videos_filename, "a") as f:
        add_to_playlist(youtube, playlist_id, video_ids, f, allow_duplicates)


def main():
    # test1()
    test2()


if __name__ == "__main__":
    main()
