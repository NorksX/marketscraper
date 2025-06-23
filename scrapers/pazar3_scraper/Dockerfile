FROM python:3.9-slim

WORKDIR /app

COPY pazar3_scraper/requirements.txt .
RUN apt-get update && apt-get install -y \
    cron \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY pazar3_scraper/pazar3_scraper.py .
COPY pazar3_scraper/ad.py .

COPY pazar3_scraper/cronjob /etc/cron.d/cronjob

RUN chmod 0644 /etc/cron.d/cronjob && \
    crontab /etc/cron.d/cronjob && \
    touch /var/log/itmk_cron.log

CMD ["cron", "-f"]