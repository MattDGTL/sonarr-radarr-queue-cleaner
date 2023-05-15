# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.

import os
import asyncio
import logging
import requests
from requests.exceptions import RequestException
from datetime import datetime, timezone
from dateutil import parser

SONARR_API_URL = (os.environ["SONARR_URL"]) + "/api/v3"
RADARR_API_URL = (os.environ["RADARR_URL"]) + "/api/v3"
LIDARR_API_URL = (os.environ["LIDARR_URL"]) + "/api/v1"
QBITTORRENT_API_URL = (os.environ["QBITTORRENT_URL"]) + "/api/v2"

SONARR_API_KEY = os.environ["SONARR_API_KEY"]
RADARR_API_KEY = os.environ["RADARR_API_KEY"]
LIDARR_API_KEY = os.environ["LIDARR_API_KEY"]
QBITTORRENT_USERNAME = os.environ["QBITTORRENT_USERNAME"]
QBITTORRENT_PASSWORD = os.environ["QBITTORRENT_PASSWORD"]

API_TIMEOUT = int(os.environ["API_TIMEOUT"])

LOG_LEVEL = (os.environ["LOG_LEVEL"]).upper() if os.environ["LOG_LEVEL"] else "INFO"

DOWNLOAD_SPEED_CUTOFF = os.environ["DOWNLOAD_SPEED_CUTOFF"]

logging.basicConfig(
    format="%(asctime)s [%(levelname)s]: %(message)s",
    level=logging._nameToLevel[LOG_LEVEL],
    handlers=[logging.StreamHandler()],
)


async def make_request(
    url, api_key=None, params=None, data=None, request_method="get", session=None
):
    try:
        headers = {"X-Api-Key": api_key}
        request = None
        if request_method == "get":
            request = (
                requests.get(url, params=params, headers=headers, data=data)
                if session is None
                else session.get(url, params=params, headers=headers, data=data)
            )
        elif request_method == "post":
            request = (
                requests.post(url, params=params, headers=headers, data=data)
                if session is None
                else session.post(url, params=params, headers=headers, data=data)
            )
        elif request_method == "delete":
            request = (
                requests.delete(url, params=params, headers=headers, data=data)
                if session is None
                else session.delete(url, params=params, headers=headers, data=data)
            )
        else:
            raise ValueError(f"Invalid request method: {request_method}")

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: request,
        )
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()
    except RequestException as e:
        logging.error(f"Error making API request to {url}: {e}")
        return None
    except ValueError as e:
        logging.error(f"Error parsing JSON response from {url}: {e}")
        return None


async def remove_stalled_downloads(app_name, api_url, api_key):
    logging.debug(f"Checking {app_name} queue...")
    queue = await make_request(
        url=f"{api_url}/queue",
        api_key=api_key,
        params={"page": "1", "pageSize": await count_records(api_url, api_key)},
    )
    removed_downloads = []
    if queue is not None and "records" in queue:
        logging.debug(f"Processing {app_name} queue...")
        for item in queue["records"]:
            logging.debug(
                f'Processing {app_name} queue item: {item["title"] if "title" in item else "Unknown"}'
            )
            if "downloadId" in item and item["downloadId"] in removed_downloads:
                logging.debug(
                    f'Skipping {app_name} queue item: {item["title"] if "title" in item else "Unknown"} because it was already removed'
                )
            elif should_clean_item(item, app_name):
                if "downloadId" in item:
                    removed_downloads.append(item["downloadId"])
                await make_request(
                    url=f'{api_url}/queue/{item["id"]}',
                    api_key=api_key,
                    params={"removeFromClient": "true", "blocklist": "true"},
                    request_method="delete",
                )
    else:
        logging.warning(f'{app_name} queue is None or missing "records" key')


def should_clean_item(item, app_name):
    # If the download is usenet rather than a torrent
    if "protocol" in item and item["protocol"] == "usenet":
        logging.debug(
            f'Skipping usenet {app_name} queue item: {item["title"] if "title" in item else "Unknown"}'
        )
        return False

    # If the download is stalled with no connections
    if (
        "errorMessage" in item
        and item["errorMessage"] == "The download is stalled with no connections"
    ):
        if (
            "status" in item
            and item["status"] == "warning"
            or item["trackedDownloadStatus"] == "warning"
        ):
            logging.info(
                f'Removing stalled {app_name} download: {item["title"] if "title" in item else "Unknown"}'
            )
            return True

    # If DOWNLOAD_SPEED_CUTOFF is set & the download is slower than this value
    if (
        DOWNLOAD_SPEED_CUTOFF
        and "trackedDownloadState" in item
        and item["trackedDownloadState"] == "downloading"
        and "estimatedCompletionTime" in item
        and "sizeleft" in item
    ):
        estimated_time_remaining = parser.parse(item["estimatedCompletionTime"])
        now = datetime.now(timezone.utc)
        time_remaining_s = (estimated_time_remaining - now).total_seconds().__abs__()
        size_left_kb = item["sizeleft"] / 1024
        download_speed_kbs = size_left_kb / time_remaining_s

        if download_speed_kbs < float(DOWNLOAD_SPEED_CUTOFF):
            logging.info(
                f'Removing slow {app_name} download ({"{:.2f}".format(download_speed_kbs)}kb/s): {item["title"] if "title" in item else "Unknown"}'
            )
            return True

    return False


async def count_records(API_URL, API_Key):
    the_queue = await make_request(url=f"{API_URL}/queue", api_key=API_Key)
    if the_queue is not None and "records" in the_queue:
        return the_queue["totalRecords"]


async def login_to_qbittorrent(session):
    await make_request(
        url=QBITTORRENT_API_URL + "/auth/login",
        session=session,
        data={"username": QBITTORRENT_USERNAME, "password": QBITTORRENT_PASSWORD},
        request_method="post",
    )


async def qbittorrent_remove_stalled_downloads(torrents, category, api_url, api_key):
    names_to_remove = []
    for torrent in torrents:
        download_speed_kbs = torrent["dlspeed"] / 1024
        if (
            torrent["state"] == "stalledDL"
            or torrent["state"] == "metaDL"
            or (
                torrent["state"] == "downloading"
                and download_speed_kbs < float(DOWNLOAD_SPEED_CUTOFF)
            )
        ):
            if torrent["category"] == category:
                names_to_remove.append(torrent["name"])

    queue = await make_request(
        url=f"{api_url}/queue",
        api_key=api_key,
        params={
            "page": "1",
            "pageSize": await count_records(SONARR_API_URL, SONARR_API_KEY),
        },
    )

    if queue is not None and "records" in queue:
        for item in queue["records"]:
            if "title" in item and item["title"] in names_to_remove:
                logging.info(
                    f'Removing stalled/slow {category} download: {item["title"] if "title" in item else "Unknown"}'
                )
                await make_request(
                    url=f'{api_url}/queue/{item["id"]}',
                    api_key=api_key,
                    params={"removeFromClient": "true", "blocklist": "true"},
                    request_method="delete",
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
            await login_to_qbittorrent(session)

            torrents = await make_request(
                url=QBITTORRENT_API_URL + "/torrents/info",
                session=session,
                params={"filter": "all"},
            )
            if SONARR_API_KEY:
                await qbittorrent_remove_stalled_downloads(
                    torrents, "tv-sonarr", SONARR_API_URL, SONARR_API_KEY
                )
            if RADARR_API_KEY:
                await qbittorrent_remove_stalled_downloads(
                    torrents, "radarr", RADARR_API_URL, RADARR_API_KEY
                )
            if LIDARR_API_KEY:
                await qbittorrent_remove_stalled_downloads(
                    torrents, "lidarr", RADARR_API_URL, LIDARR_API_KEY
                )
        else:
            if SONARR_API_KEY:
                await remove_stalled_downloads("Sonarr", SONARR_API_URL, SONARR_API_KEY)
            if RADARR_API_KEY:
                await remove_stalled_downloads("Radarr", RADARR_API_URL, RADARR_API_KEY)
            if LIDARR_API_KEY:
                await remove_stalled_downloads("Lidarr", LIDARR_API_URL, LIDARR_API_KEY)

        logging.debug(
            f"Finished processing queues. Sleeping for {API_TIMEOUT} seconds."
        )
        await asyncio.sleep(API_TIMEOUT)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
