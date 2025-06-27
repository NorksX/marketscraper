FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY it_mk_scraper.py .
COPY ad.py .

CMD ["/usr/local/bin/python", "./it_mk_scraper.py"]
