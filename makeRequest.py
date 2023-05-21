import requests
import logging
import asyncio


async def make_request(request: requests.Request, is_get_request=True):
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: request,
        )
        response.raise_for_status()

        if is_get_request and response.status_code != 204:
            return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making API request to {request.url}: {e}")
        return None
    except ValueError as e:
        logging.error(f"Error parsing JSON response from {request.url}: {e}")
        return None
