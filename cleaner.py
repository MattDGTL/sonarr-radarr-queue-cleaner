# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.

import os
import asyncio
import logging
import requests
import qbittorrentAPI
import arrAPI

SONARR_API_URL = (os.environ["SONARR_URL"]) + "/api/v3"
RADARR_API_URL = (os.environ["RADARR_URL"]) + "/api/v3"
LIDARR_API_URL = (os.environ["LIDARR_URL"]) + "/api/v1"

SONARR_API_KEY = os.environ["SONARR_API_KEY"]
RADARR_API_KEY = os.environ["RADARR_API_KEY"]
LIDARR_API_KEY = os.environ["LIDARR_API_KEY"]

QBITTORRENT_API_URL = (os.environ["QBITTORRENT_URL"]) + "/api/v2"
QBITTORRENT_USERNAME = os.environ["QBITTORRENT_USERNAME"]
QBITTORRENT_PASSWORD = os.environ["QBITTORRENT_PASSWORD"]


API_TIMEOUT = int(os.environ["API_TIMEOUT"])

DOWNLOAD_SPEED_CUTOFF = os.environ["DOWNLOAD_SPEED_CUTOFF"]

LOG_LEVEL = (os.environ["LOG_LEVEL"]).upper() if os.environ["LOG_LEVEL"] else "INFO"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s]: %(message)s",
    level=logging._nameToLevel[LOG_LEVEL],
    handlers=[logging.StreamHandler()],
)


async def main():
    if not SONARR_API_KEY:
        logging.warning("Sonarr API key is not set. Skipping Sonarr queue checks.")
    if not RADARR_API_KEY:
        logging.warning("Radarr API key is not set. Skipping Radarr queue checks.")
    if not LIDARR_API_KEY:
        logging.warning("Lidarr API key is not set. Skipping Lidarr queue checks.")

    while True:
        logging.debug("Running media-tools script")

        if QBITTORRENT_API_URL and QBITTORRENT_USERNAME and QBITTORRENT_PASSWORD:
            session = requests.Session()

            logging.debug("Logging into qBittorrent")
            await qbittorrentAPI.login_to_qbittorrent(session)

            torrents = await qbittorrentAPI.get_torrents(session)
            if SONARR_API_KEY:
                await qbittorrentAPI.remove_stalled_downloads(
                    session, torrents, "tv-sonarr", SONARR_API_URL, SONARR_API_KEY
                )
            if RADARR_API_KEY:
                await qbittorrentAPI.remove_stalled_downloads(
                    session, torrents, "radarr", RADARR_API_URL, RADARR_API_KEY
                )
            if LIDARR_API_KEY:
                await qbittorrentAPI.remove_stalled_downloads(
                    session, torrents, "lidarr", RADARR_API_URL, LIDARR_API_KEY
                )

            await qbittorrentAPI.logout_of_qbittorrent(session)
        else:
            if SONARR_API_KEY:
                await arrAPI.remove_stalled_downloads(
                    "Sonarr", SONARR_API_URL, SONARR_API_KEY
                )
            if RADARR_API_KEY:
                await arrAPI.remove_stalled_downloads(
                    "Radarr", RADARR_API_URL, RADARR_API_KEY
                )
            if LIDARR_API_KEY:
                await arrAPI.remove_stalled_downloads(
                    "Lidarr", LIDARR_API_URL, LIDARR_API_KEY
                )

        logging.debug(
            f"Finished processing queues. Sleeping for {API_TIMEOUT} seconds."
        )
        await asyncio.sleep(API_TIMEOUT)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
