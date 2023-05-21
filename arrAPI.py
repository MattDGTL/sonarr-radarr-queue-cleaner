import requests
import makeRequest
import os
import logging
from datetime import datetime, timezone
from dateutil import parser

SONARR_API_URL = (os.environ["SONARR_URL"]) + "/api/v3"
RADARR_API_URL = (os.environ["RADARR_URL"]) + "/api/v3"
LIDARR_API_URL = (os.environ["LIDARR_URL"]) + "/api/v1"

SONARR_API_KEY = os.environ["SONARR_API_KEY"]
RADARR_API_KEY = os.environ["RADARR_API_KEY"]
LIDARR_API_KEY = os.environ["LIDARR_API_KEY"]

DOWNLOAD_SPEED_CUTOFF = os.environ["DOWNLOAD_SPEED_CUTOFF"]


async def get_queue(api_url: str, api_key: str):
    return await makeRequest.make_request(
        requests.get(
            f"{api_url}/queue",
            params={"page": "1", "pageSize": await count_records(api_url, api_key)},
            headers={"X-Api-Key": api_key},
        )
    )


async def count_records(api_url: str, api_key: str):
    the_queue = await makeRequest.make_request(
        requests.get(
            f"{api_url}/queue",
            headers={"X-Api-Key": api_key},
        )
    )
    if the_queue is not None and "records" in the_queue:
        return the_queue["totalRecords"]


async def delete_queue_element(
    api_url: str, api_key: str, item, remove_from_client=True, blocklist=True
):
    await makeRequest.make_request(
        requests.delete(
            f'{api_url}/queue/{item["id"]}',
            params={
                "removeFromClient": "true" if remove_from_client else "false",
                "blocklist": "true" if blocklist else "false",
            },
            headers={"X-Api-Key": api_key},
        ),
        False,
    )


async def search_sonarr_season(series_id: str, season_number: str):
    await makeRequest.make_request(
        requests.post(
            SONARR_API_URL + "/command",
            json={
                "name": "SeasonSearch",
                "seasonNumber": season_number,
                "seriesId": series_id,
            },
            headers={"X-Api-Key": SONARR_API_KEY},
        ),
        False,
    )


async def remove_stalled_downloads(app_name: str, api_url: str, api_key: str):
    logging.debug(f"Checking {app_name} queue...")
    queue = await get_queue(api_url, api_key)
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
                await delete_queue_element(api_url, api_key, item)
    else:
        logging.warning(f'{app_name} queue is None or missing "records" key')


def should_clean_item(item, app_name: str):
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
