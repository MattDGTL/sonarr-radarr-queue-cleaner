# sonarr-radarr-queue-cleaner
A simple Sonarr and Radarr script to clean out stalled downloads.
Couldn't find a python script to do this job so I figured why not give it a try.

Details:

This script checks every 10 minutes Sonarr's and Radarr's queue json information for downloads that has a `status` of `Warning` and or `errorMessage` that states `The download is stalled with no connections` for each item in the queue and removes it, informs download client to delete files and sends the release to blocklist to prevent it from re-downloading.

You can how often it checks via `API_TIMEOUT=`. It's currently set to 600 seconds (10 minutes). You probably should change this to check every hour or more.

The script uses asyncio to allow each call to wait for a response before proceeding.
Logs everything and streams the info. You can replace with good ol' print if you like just remove the `# Set up logging` section and change all `logging.error` & `logging.info` to `print`.

This script was created to work in a docker container so the included files are necessary.
to use in a docker container, copy folder to the machine hosting your docker, `CD` into the directory where the files are located and enter these following 2 commands:

1# `docker build -t media-cleaner .`

2#. `docker run -d --name -e SONARR_API_KEY='123456' -e RADARR_API_KEY='123456' -e SONARR_URL='http://sonarr:8989' -e RADARR_URL='http://radarr:7878' -e API_TIMEOUT='600' media-cleaner media-cleaner`

Or simply run: `docker run -d --name -e SONARR_API_KEY='123456' -e RADARR_API_KEY='123456' -e SONARR_URL='http://sonarr:8989' -e RADARR_URL='http://radarr:7878' -e API_TIMEOUT='600' kjames2001/media-cleaner:latest`
