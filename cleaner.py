# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.

import os
import asyncio
import logging
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
    
async def remove_stalled_downloads(appName, apiURL, apiKey):
    logging.info(f'Checking {appName} queue...')
    url = f'{apiURL}/queue'
    queue = await make_api_request(url, apiKey, {'page': '1', 'pageSize': await count_records(apiURL, apiKey)})
    if queue is not None and 'records' in queue:
        logging.info(f'Processing {appName} queue...')
        for item in queue['records']:
            if shouldCleanItem(item):
                logging.info(f'Removing stalled {appName} download: {item["title"] if "title" in item else "Unknown"}')
                await make_api_delete(f'{apiURL}/queue/{item["id"]}', apiKey, {'removeFromClient': 'true', 'blocklist': 'true'})
    else:
        logging.warning(f'{appName} queue is None or missing "records" key')

def shouldCleanItem(item):
    if 'errorMessage' in item and item['errorMessage'] == 'The download is stalled with no connections':
        if('status' in item):
            return item['status'] == 'warning'
        return item['trackedDownloadStatus'] == 'warning'
    return False

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

        if SONARR_API_KEY:
            await remove_stalled_downloads('Sonarr', SONARR_API_URL, SONARR_API_KEY)
        else:
            logging.warning('Sonarr API key is not set. Skipping Sonarr queue check.')

        if RADARR_API_KEY:
            await remove_stalled_downloads('Radarr', RADARR_API_URL, RADARR_API_KEY)
        else:
            logging.warning('Radarr API key is not set. Skipping Radarr queue check.')

        if LIDARR_API_KEY:            
            await remove_stalled_downloads('Lidarr', LIDARR_API_URL, LIDARR_API_KEY)
        else:
            logging.warning('Lidarr API key is not set. Skipping Lidarr queue check.')

        logging.info(f"Finished processing queues. Sleeping for {API_TIMEOUT} seconds.")
        await asyncio.sleep(API_TIMEOUT)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
