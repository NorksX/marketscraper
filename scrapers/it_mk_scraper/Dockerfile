FROM python:3.9-slim

WORKDIR /app

COPY it_mk_scraper/requirements.txt .
RUN apt-get update && apt-get install -y \
    cron \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY it_mk_scraper/it_mk_scraper.py .
COPY it_mk_scraper/ad.py .

COPY it_mk_scraper/cronjob /etc/cron.d/cronjob

RUN chmod 0644 /etc/cron.d/cronjob && \
    crontab /etc/cron.d/cronjob && \
    touch /var/log/itmk_cron.log

CMD ["cron", "-f"]