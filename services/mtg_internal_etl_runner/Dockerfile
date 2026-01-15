FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r services/mtg_internal_etl_runner/requirements.txt

# Install internal packages used by the ETL runner (fail-fast)
RUN pip install -e packages/mtg_internal_etl
RUN pip install -e packages/mtg_internal_client
RUN pip install -e packages/mtg_internal_core

CMD ["python", "services/mtg_internal_etl_runner/etl_runner.py"]
ENV PYTHONPATH=/app

RUN pip install --upgrade pip
RUN pip install -r services/mtg_internal_etl_runner/requirements.txt

CMD ["python", "services/mtg_internal_etl_runner/etl_runner.py"]
