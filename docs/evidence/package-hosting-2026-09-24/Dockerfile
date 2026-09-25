FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt

RUN groupadd --gid 10001 accessflow \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin accessflow \
    && mkdir -p /results \
    && chown accessflow:accessflow /results

COPY accessflow/ ./accessflow
COPY agent/ ./agent
COPY harness/ ./harness
COPY docs/ ./docs
COPY scenarios/ ./scenarios
COPY audio/ ./audio
COPY frames/ ./frames
COPY assets/ ./assets
COPY hosting/start_vision_server.py ./hosting/
COPY submission.yaml ./
COPY runtime_profile.json ./
COPY eval_submission.py ./
COPY run_local.py ./
COPY package_manifest.json ./


USER 10001:10001
ENTRYPOINT ["python", "eval_submission.py"]
CMD [".", "--reps", "3", "--out", "/results/results.json"]
