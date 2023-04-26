# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.

import os
import asyncio
import logging
import validators
import requests
from requests.exceptions import RequestException

SONARR_API_URL = (os.environ['SONARR_URL']) + "/api/v3"
RADARR_API_URL = (os.environ['RADARR_URL']) + "/api/v3"
LIDARR_API_URL = (os.environ['LIDARR_URL']) + "/api/v1"

SONARR_API_KEY = (os.environ['SONARR_API_KEY'])
RADARR_API_KEY = (os.environ['RADARR_API_KEY'])
LIDARR_API_KEY = (os.environ['LIDARR_API_KEY'])

# Timeout for API requests in seconds
API_TIMEOUT = int(os.environ['API_TIMEOUT'])

LOG_LEVEL = (os.environ['LOG_LEVEL']).upper() if os.environ['LOG_LEVEL'] else 'WARN'

# Set up logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s', 
    level=logging._nameToLevel[LOG_LEVEL], 
    handlers=[logging.StreamHandler()]
)

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

# Function to make API delete with error handling
async def make_api_delete(url, api_key, params=None):
    try:
        headers = {'X-Api-Key': api_key}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.delete(url, params=params, headers=headers))
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None
    
# Function to remove stalled Sonarr downloads
async def remove_stalled_sonarr_downloads():
    logging.info('Checking Sonarr queue...')
    sonarr_url = f'{SONARR_API_URL}/queue'
    sonarr_queue = await make_api_request(sonarr_url, SONARR_API_KEY, {'page': '1', 'pageSize': await count_records(SONARR_API_URL,SONARR_API_KEY)})
    if sonarr_queue is not None and 'records' in sonarr_queue:
        logging.info('Processing Sonarr queue...')
        for item in sonarr_queue['records']:
            if shouldCleanItem(item):
                logging.info(f'Removing stalled Sonarr download: {item["title"] if "title" in item else "Unknown"}')
                await make_api_delete(f'{SONARR_API_URL}/queue/{item["id"]}', SONARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
    else:
        logging.warning('Sonarr queue is None or missing "records" key')

# Function to remove stalled Radarr downloads
async def remove_stalled_radarr_downloads():
    logging.info('Checking radarr queue...')
    radarr_url = f'{RADARR_API_URL}/queue'
    radarr_queue = await make_api_request(radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY)})
    if radarr_queue is not None and 'records' in radarr_queue:
        logging.info('Processing Radarr queue...')
        for item in radarr_queue['records']:
            if shouldCleanItem(item):
                logging.info(f'Removing stalled Radarr download: {item["title"] if "title" in item else "Unknown"}')
                await make_api_delete(f'{RADARR_API_URL}/queue/{item["id"]}', RADARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
    else:
        logging.warning('Radarr queue is None or missing "records" key')

# Function to remove stalled Lidarr downloads
async def remove_stalled_lidarr_downloads():
    logging.info('Checking Lidarr queue...')
    lidarr_url = f'{LIDARR_API_URL}/queue'
    lidarr_queue = await make_api_request(lidarr_url, LIDARR_API_KEY, {'page': '1', 'pageSize': await count_records(LIDARR_API_URL,LIDARR_API_KEY)})
    if lidarr_queue is not None and 'records' in lidarr_queue:
        logging.info('Processing Lidarr queue...')
        for item in lidarr_queue['records']:
            if shouldCleanItem(item):
                logging.info(f'Removing stalled Lidarr download: {item["title"] if "title" in item else "Unknown"}')
                await make_api_delete(f'{LIDARR_API_URL}/queue/{item["id"]}', LIDARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
    else:
        logging.warning('Lidarr queue is None or missing "records" key')

def shouldCleanItem(item):
    return (item['status'] == 'warning' or item['trackedDownloadStatus'] == 'warning') and item['errorMessage'] == 'The download is stalled with no connections'

# Make a request to view and count items in queue and return the number.
async def count_records(API_URL, API_Key):
    the_url = f'{API_URL}/queue'
    the_queue = await make_api_request(the_url, API_Key)
    if the_queue is not None and 'records' in the_queue:
        return the_queue['totalRecords']

# Main function
async def main():
    while True:
        logging.info('Running media-tools script')

        if SONARR_API_URL is not None and validators.url(SONARR_API_URL) and SONARR_API_KEY is not None:
            await remove_stalled_sonarr_downloads()
        else:
            logging.warning('Sonarr API URL or API key is not set. Skipping Sonarr queue check.')

        if RADARR_API_URL is not None and validators.url(RADARR_API_URL) and RADARR_API_KEY is not None:
            await remove_stalled_radarr_downloads()
        else:
            logging.warning('Radarr API URL or API key is not set. Skipping Radarr queue check.')

        if LIDARR_API_URL is not None and validators.url(LIDARR_API_URL) and LIDARR_API_KEY is not None:            
            await remove_stalled_lidarr_downloads()
        else:
            logging.warning('Lidarr API URL or API key is not set. Skipping Lidarr queue check.')

        logging.info("Finished processing queues. Sleeping for {API_TIMEOUT} seconds.")
        await asyncio.sleep(API_TIMEOUT)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
