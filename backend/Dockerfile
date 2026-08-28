FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

COPY . .
COPY ../deploy/backend-entrypoint.sh /usr/local/bin/domaintwin-entrypoint
RUN chmod +x /usr/local/bin/domaintwin-entrypoint

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/domaintwin-entrypoint"]
CMD ["web"]
