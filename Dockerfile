# Runtime image for lemma miner/validator.
#
# Lean verification runs via `docker exec` against a long-lived worker container
# mounted via /var/run/docker.sock — the full Docker engine belongs on the host,
# not in this image.
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY lemma ./lemma
RUN pip install --no-cache-dir .
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["lemma"]
CMD ["validator", "start"]
