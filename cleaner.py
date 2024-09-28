# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.
# 
# Purpose of script: 
# Removes stale and orphan downloads from Sonarr/Radarr

########### Import Libraries
import os
import asyncio
import logging
import requests
from requests.exceptions import RequestException
import json
from dateutil.relativedelta import relativedelta as rd

########### Enabling Logging
# Set up logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s', 
    level=logging.INFO, 
    handlers=[logging.StreamHandler()]
)

########### Loading Parameters
# Sonarr and Radarr API endpoints
SONARR_API_URL = (os.environ['SONARR_URL']) + "/api/v3"
RADARR_API_URL = (os.environ['RADARR_URL']) + "/api/v3"

# API key for Sonarr and Radarr
SONARR_API_KEY = (os.environ['SONARR_API_KEY'])
RADARR_API_KEY = (os.environ['RADARR_API_KEY'])

# Timeout for API requests in seconds
API_TIMEOUT = int(os.environ['TIMEOUT']) # 10 minutes

########### Shared Functions
# Function to make API requests with error handling
async def make_api_request(url, api_key, params=None):
    try:
        headers = {'X-Api-Key': api_key}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(url, params=params, headers=headers))
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None

# Make a request to view and count items in queue and return the number.
async def count_records(API_URL, API_Key, params=None):
    the_url = f'{API_URL}/queue'
    the_queue = await make_api_request(the_url, API_Key, params)
    if the_queue is not None and 'records' in the_queue:
        return the_queue['totalRecords']

# Function to make API delete with error handling
async def make_api_delete(url, api_key, params=None):
    try:
        headers = {'X-Api-Key': api_key}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.delete(url, params=params, headers=headers))
        response.raise_for_status()        
        if response.status_code == 200: 
            return None
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None

########### STALE Downloads
### Stale downloads are those that are still in progress, but are not continuing as they are stuck (stale)
### Script will kill those downloads, and ban the trackers

# Function to remove stalled Sonarr downloads
async def remove_stalled_sonarr_downloads():
    logging.info('> Checking Sonarr queue for stalled downloads...')
    sonarr_url = f'{SONARR_API_URL}/queue'
    sonarr_queue = await make_api_request(sonarr_url, SONARR_API_KEY, {'page': '1', 'pageSize': await count_records(SONARR_API_URL,SONARR_API_KEY)})
    if sonarr_queue is not None and 'records' in sonarr_queue:
        # logging.info('Processing Sonarr queue for stalled downloads...')
        stalled_count = 0
        for item in sonarr_queue['records']:
            if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                # logging.info(f'>>> > Checking the status of {item["title"]}')
                if item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections':
                    logging.info(f'Removing stalled Sonarr download: {item["title"]}')
                    stalled_count += 1
                    await make_api_delete(f'{SONARR_API_URL}/queue/{item["id"]}', SONARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
            else:
                logging.warning('Skipping item in Sonarr queue due to missing or invalid keys')
        if stalled_count == 0:
            logging.info('>>> No Sonarr stalled downloads found.')
    else:
        logging.warning('Sonarr queue is None or missing "records" key')

# Function to remove stalled Radarr downloads
async def remove_stalled_radarr_downloads():
    logging.info('> Checking Radarr queue for stalled downloads...')
    radarr_url = f'{RADARR_API_URL}/queue'
    radarr_queue = await make_api_request(radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY)})
    if radarr_queue is not None and 'records' in radarr_queue:
        # logging.info('Processing Radarr queue for stalled downloads...')
        stalled_count = 0
        for item in radarr_queue['records']:
            if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                # logging.info(f'>>> > Checking the status of {item["title"]}')
                if item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections':
                    logging.info(f'Removing stalled Radarr download: {item["title"]}')
                    stalled_count += 1
                    await make_api_delete(f'{RADARR_API_URL}/queue/{item["id"]}', RADARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
            else:
                ogging.warning('Skipping item in Radarr queue due to missing or invalid keys')
        if stalled_count == 0:
            logging.info('>>> No Sonarr stalled downloads found.')
    else:
        logging.warning('Radarr queue is None or missing "records" key')

########### ORPHAN Downloads
### Orphan downloads are those that are still in progress, but not linked to a TV Show / Movie anymore 
### This occurs when a Download is initiated and still in progress, and in the meantime the TV Show / Movie is deleted from Radarr/Sonarr
### Script will kill those downloads but not ban them (for future downloads, if needed)

# Function to remove Sonarr queue items linked to no movies (orphan downloads)
async def remove_orphan_sonarr_downloads():
    logging.info('> Checking Sonarr queue for orphan downloads...')
    sonarr_url = f'{SONARR_API_URL}/queue'
    sonarr_queue = await make_api_request(sonarr_url, SONARR_API_KEY, {'page': '1', 'pageSize': await count_records(SONARR_API_URL,SONARR_API_KEY)})
    sonarr_url = f'{SONARR_API_URL}/queue?includeUnknownSeriesItems=true'
    sonarr_queue_incl_unknown = await make_api_request(sonarr_url, SONARR_API_KEY, {'page': '1', 'pageSize': await count_records(SONARR_API_URL,SONARR_API_KEY,'includeUnknownSeriesItems=true')})
    if sonarr_queue_incl_unknown is not None and 'records' in sonarr_queue_incl_unknown:
        Full_list = {}
        OK_list = {}
        for item in sonarr_queue_incl_unknown['records']:
            Full_list[item['id']] = item['title']
        if sonarr_queue is not None and 'records' in sonarr_queue:
            for item in sonarr_queue['records']:
                OK_list[item['id']] = item['title']
        else:
            logging.warning('Sonarr queue linked to movies is  None or missing "records" key')
        orphan_downloads = {id: Full_list[id] for id in Full_list if id not in OK_list}
        if len(orphan_downloads) == 0:
            logging.info('>>> No Sonarr orphan downloads found.')
        else:
            for id in orphan_downloads:
                logging.info(f'Removing orphan Sonarr download: {orphan_downloads[id]}')
                await make_api_delete(f'{SONARR_API_URL}/queue/{id}', SONARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'false'})
    else:
        logging.warning('Sonarr queue is None or missing "records" key')

# Function to remove Radarr queue items linked to no movies (orphan downloads)
async def remove_orphan_radarr_downloads():
    logging.info('> Checking Radarr queue for orphan downloads...')
    radarr_url = f'{RADARR_API_URL}/queue'
    radarr_queue = await make_api_request(radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY)})
    radarr_url = f'{RADARR_API_URL}/queue?includeUnknownMovieItems=true'
    radarr_queue_incl_unknown = await make_api_request(radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY,'includeUnknownMovieItems=true')})
    if radarr_queue_incl_unknown is not None and 'records' in radarr_queue_incl_unknown:
        Full_list = {}
        OK_list = {}
        for item in radarr_queue_incl_unknown['records']:
            Full_list[item['id']] = item['title']
        if radarr_queue is not None and 'records' in radarr_queue:
            for item in radarr_queue['records']:
                OK_list[item['id']] = item['title']
        else:
            logging.warning('Radarr queue linked to movies is  None or missing "records" key')
        orphan_downloads = {id: Full_list[id] for id in Full_list if id not in OK_list}
        if len(orphan_downloads) == 0:
            logging.info('>>> No Radarr orphan downloads found.')
        else:
            for id in orphan_downloads:
                logging.info(f'Removing orphan Radarr download: {orphan_downloads[id]}')
                await make_api_delete(f'{RADARR_API_URL}/queue/{id}', RADARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'false'})
    else:
        logging.warning('Radarr queue is None or missing "records" key')
        

# Main function
async def main():
    while True:
        logging.info('*******************************************************************************************************************')
        logging.info('Running queue cleaner for Radarr/Sonarr.')
        await remove_stalled_sonarr_downloads()
        await remove_stalled_radarr_downloads()
        await remove_orphan_radarr_downloads()
        await remove_orphan_sonarr_downloads()
        fmt = '{0.days} days {0.hours} hours {0.minutes} minutes {0.seconds} seconds'
        logging.info(f'Finished running queue cleaner for Radarr/Sonarr. Sleeping for {fmt.format(rd(seconds=API_TIMEOUT))}.')
        await asyncio.sleep(API_TIMEOUT)


if __name__ == '__main__':
    asyncio.run(main())
