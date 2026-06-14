# Seed image: runs seed.py against the in-cluster API to rebuild the curated
# tree in a fresh DB. Needs psql (seed.py verifies the root insert via a direct
# DB query) plus Python stdlib. Run as an ArgoCD PostSync hook Job.
#
# Env (see seed.py):
#   SEED_BASE_URL  e.g. http://api:3200
#   SEED_PG_DSN    e.g. postgresql://familytree:familytree@postgres:5432/familytree
FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /seed
COPY . .
ENTRYPOINT ["python", "seed.py"]
