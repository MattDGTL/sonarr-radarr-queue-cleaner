import requests
import os
import makeRequest
import arrAPI
import logging
import re

QBITTORRENT_API_URL = (os.environ["QBITTORRENT_URL"]) + "/api/v2"
QBITTORRENT_USERNAME = os.environ["QBITTORRENT_USERNAME"]
QBITTORRENT_PASSWORD = os.environ["QBITTORRENT_PASSWORD"]

DOWNLOAD_SPEED_CUTOFF = os.environ["DOWNLOAD_SPEED_CUTOFF"]


async def login_to_qbittorrent(session: requests):
    await makeRequest.make_request(
        session.post(
            QBITTORRENT_API_URL + "/auth/login",
            data={"username": QBITTORRENT_USERNAME, "password": QBITTORRENT_PASSWORD},
        ),
        False,
    )


async def logout_of_qbittorrent(session: requests):
    await makeRequest.make_request(
        session.post(QBITTORRENT_API_URL + "/auth/logout"), False
    )


async def delete_torrent(session: requests, torrent):
    await makeRequest.make_request(
        session.post(
            f"{QBITTORRENT_API_URL}/torrents/delete",
            data={
                "hashes": torrent["hash"],
                "deleteFiles": "true",
            },
        ),
        False,
    )


async def get_torrents(session: requests):
    return await makeRequest.make_request(
        session.get(QBITTORRENT_API_URL + "/torrents/info", params={"filter": "all"})
    )


def get_torrents_to_remove(torrents, category: str):
    torrents_to_remove = []
    if torrents:
        for torrent in torrents:
            if torrent["category"] == category:
                logging.debug(f'Processing {category} queue item: {torrent["name"]}')
                if should_remove_torrent(torrent, category):
                    torrents_to_remove.append(torrent)
    return torrents_to_remove


def should_remove_torrent(torrent, category: str):
    download_speed_kbs = torrent["dlspeed"] / 1024
    remove_torrent = False

    if torrent["state"] == "stalledDL":
        logging.info(f'Removing stalled {category} download: {torrent["name"]}')
        remove_torrent = True

    if torrent["time_active"] > 60:
        if torrent["state"] == "metaDL":
            logging.info(
                f'Removing stuck downloading metadata {category} download: {torrent["name"]}'
            )
            remove_torrent = True

        elif (
            DOWNLOAD_SPEED_CUTOFF
            and torrent["state"] == "downloading"
            and download_speed_kbs < float(DOWNLOAD_SPEED_CUTOFF)
        ):
            logging.info(
                f'Removing slow {category} download ({"{:.2f}".format(download_speed_kbs)}kb/s): {torrent["name"]}'
            )
            remove_torrent = True

        elif torrent["state"] == "downloading" and torrent["num_complete"] == 0:
            logging.info(f'Removing seedless {category} download: {torrent["name"]}')
            remove_torrent = True
    return remove_torrent


async def remove_stalled_downloads(
    session: requests, torrents, category: str, api_url: str, api_key: str
):
    torrents_to_remove = get_torrents_to_remove(torrents, category)
    if torrents_to_remove:
        queue = await arrAPI.get_queue(api_url, api_key)

        if queue is not None and "records" in queue:
            for torrent in torrents_to_remove:
                for item in queue["records"]:
                    if "title" in item and (
                        torrent["name"] in item["title"]
                        or item["title"] in torrent["name"]
                    ):
                        if category == "tv-sonarr":
                            SEASON_NUMBER = parse_season_number(item)
                            EPISODE_NUMBER = parse_episode_number(item)
                            if (
                                SEASON_NUMBER and EPISODE_NUMBER
                            ) or SEASON_NUMBER == None:
                                await arrAPI.delete_queue_element(
                                    api_url, api_key, item
                                )
                            elif SEASON_NUMBER:
                                await arrAPI.delete_queue_element(
                                    api_url, api_key, item, remove_from_client=False
                                )
                                await delete_torrent(session, torrent)
                                await arrAPI.search_sonarr_season(
                                    item["seriesId"], SEASON_NUMBER
                                )
                            else:
                                logging.warning(
                                    f'Did not delete and re-search sonarr download {item["title"]}'
                                )
                        else:
                            await arrAPI.delete_queue_element(api_url, api_key, item)
                        break


def parse_season_number(item):
    if "seasonNumber" in item:
        return item["seasonNumber"]
    else:
        PARSED_SEASON_NUMBER = re.search(r"S\d\d|s\d\d", item["title"])
        if PARSED_SEASON_NUMBER:
            return int(PARSED_SEASON_NUMBER.group(0)[1:])


def parse_episode_number(item):
    if "episode" in item and "episodeNumber" in item["episode"]:
        return item["episode"]["episodeNumber"]
    else:
        PARSED_EPISODE_NUMBER = re.search(r"E\d\d|e\d\d", item["title"])
        if PARSED_EPISODE_NUMBER:
            return int(PARSED_EPISODE_NUMBER.group(0)[1:])
