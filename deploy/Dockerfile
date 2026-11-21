# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
# One image for every connected plugin of the pack; `PLUGIN` picks which server runs. Standard library only.
FROM python:3.13.5-slim-bookworm
RUN useradd --create-home --uid 10001 plugin
WORKDIR /app
COPY lib ./lib
COPY sdk ./sdk
COPY expansion ./expansion
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/lib DATA_DIR=/data
RUN mkdir /data && chown plugin /data
USER plugin
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os, urllib.request as u; u.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health', timeout=4)"
CMD ["sh", "-c", "exec python expansion/*/plugins/${PLUGIN}/server.py"]
