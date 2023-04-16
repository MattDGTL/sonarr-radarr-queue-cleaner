FROM python:3.9-slim-buster

ENV SONARR_URL='http://sonarr:8989'
ENV SONARR_API_KEY=123456
ENV RADARR_URL='http://radarr:7878'
ENV RADARR_API_KEY=123456
ENV API_TIMEOUT='*/5 * * * *'

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "cleaner.py"]
