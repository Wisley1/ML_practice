FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PIP_PROGRESS_BAR=on
ENV PIP_DEFAULT_TIMEOUT=120
ENV TOKENIZERS_PARALLELISM=false

COPY requirements.txt /tmp/requirements.txt
RUN echo "=== [1/2] PyTorch (CPU wheel, ~100–200 MB download) ===" \
    && pip install --no-cache-dir "torch>=2.1.0" \
        --index-url https://download.pytorch.org/whl/cpu \
        --progress-bar on

RUN awk '!/^torch/ && NF' /tmp/requirements.txt > /tmp/requirements-notorch.txt \
    && echo "=== [2/2] Остальные пакеты: transformers, streamlit, sklearn, … (ещё много MB) ===" \
    && pip install --no-cache-dir -r /tmp/requirements-notorch.txt --progress-bar on

COPY app ./app
COPY scripts ./scripts
COPY core ./core
COPY alembic ./alembic
COPY alembic.ini .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
