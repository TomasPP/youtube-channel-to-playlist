Forked project includes workaround described here: https://github.com/RobbieClarken/youtube-channel-to-playlist/issues/5#issuecomment-524624562

# YouTube Channel to Playlist

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/RobbieClarken/youtube-channel-to-playlist/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)


Keeping track of which YouTube videos you have watched can be tricky,
especially because the "WATCHED" indicator seems to be ephemeral. This script
allows you to add all videos from a YouTube channel to a playlist that you
control so you can order them as you please and remove them once they've been
watched.

# Installation

Requirements: Python 3.6 or later.

1. Install this application with pip:

    ```bash
    python3 -m pip install git+https://github.com/RobbieClarken/youtube-channel-to-playlist
    ```

2. Create a project through the [Google Cloud Console](https://console.cloud.google.com/).
3. Enable your project to use the YouTube Data API via the [APIs &
   Services Dashboard](https://console.cloud.google.com/apis/dashboard).
4. Create an OAuth Client ID for a native application through the
   [Credentials](https://console.cloud.google.com/apis/credentials) page under APIs &
   Services.
5. Download the OAuth client secrets JSON file from the
   [Credentials](https://console.cloud.google.com/apis/credentials) page and
   rename it to `client_secrets.json`.

# Usage

```bash
channel_to_playlist --secrets client_secrets.json source-channel-id target-playlist-id
```

where `source-channel-id` and `target-playlist-id` can be found from the URLs of
the YouTube channel and playlist.

For example, to copy videos from the [PyCon 2015 Channel](https://www.youtube.com/channel/UCgxzjK6GuOHVKR_08TT4hJQ)
to [this playlist](https://www.youtube.com/playlist?list=PLlgnub_DBR_CszAWpJypwst0OFDxW6jOJ)
you would run:

```bash
channel_to_playlist --secrets client_secrets.json UCgxzjK6GuOHVKR_08TT4hJQ PLlgnub_DBR_CszAWpJypwst0OFDxW6jOJ
```

If you only want to add videos published after or before a certain date, you can use the `--after`
and `--before` options:


```bash
channel_to_playlist --after 2018-05-21 --before 2018-06-30 UCgxzjK6GuOHVKR_08TT4hJQ PLlgnub_DBR_CszAWpJypwst0OFDxW6jOJ
```

The script will store the video IDs that are added to the playlist in a file
and skip these videos if it is run again. This allows you to re-run the script
when new videos are uploaded to the channel.

To add videos which already exist in the playlist, use the `--allow-duplicates` switch, as shown in the following example:

```bash
channel_to_playlist --secrets client_secrets.json UCgxzjK6GuOHVKR_08TT4hJQ PLlgnub_DBR_CszAWpJypwst0OFDxW6jOJ --allow-duplicates
```
