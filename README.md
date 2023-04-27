# sonarr-radarr-queue-cleaner

A simple Sonarr, Radarr & Lidarr script to clean out stalled/slow downloads.
Couldn't find a python script to do this job so I figured why not give it a try.

Details:

This script checks every 10 minutes (configurable) Sonarr's and Radarr's queue json information for downloads that has an `errorMessage` that states `The download is stalled with no connections` or a `timeleft` that's greater than a day for each item in the queue and removes it, informs download client to delete files and sends the release to blocklist to prevent it from re-downloading.

The script uses asyncio to allow each call to wait for a response before proceeding.
Logging defaults to the `INFO` level, but you can configure this to be e.g. `DEBUG` to get more information.

This script was created to work in a docker container so the included files are necessary.
to use in a docker container, copy folder to the machine hosting your docker, `CD` into the directory where the files are located and enter these following 2 commands:

1# `docker build -t media-cleaner .`

2#. `docker run -d --name media-cleaner -e SONARR_API_KEY='123456' -e RADARR_API_KEY='123456' -e SONARR_URL='http://sonarr:8989' -e RADARR_URL='http://radarr:7878' -e API_TIMEOUT='600' -LOG_LEVEL='INFO' media-cleaner`
