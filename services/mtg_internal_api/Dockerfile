FROM python:3.11-slim
WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r services/mtg_internal_api/requirements.txt

# Install internal packages in editable mode so `import mtg_internal_client` works
RUN pip install -e packages/mtg_internal_client
RUN pip install -e packages/mtg_internal_core
RUN pip install -e packages/mtg_internal_etl

EXPOSE 8000
CMD ["uvicorn", "services.mtg_internal_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
