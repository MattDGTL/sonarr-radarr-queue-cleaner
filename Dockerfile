FROM python:3.9-slim-buster

ENV SONARR_URL='http://sonarr:8989'
ENV SONARR_API_KEY=
ENV RADARR_URL='http://radarr:7878'
ENV RADARR_API_KEY=
ENV LIDARR_URL='http://lidarr:8686'
ENV LIDARR_API_KEY=
ENV QBITTORRENT_URL='http://qbit:8080'
ENV QBITTORRENT_USERNAME=
ENV QBITTORRENT_PASSWORD=
ENV API_TIMEOUT=600
ENV LOG_LEVEL='INFO'
ENV DOWNLOAD_SPEED_CUTOFF=

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "cleaner.py"]
