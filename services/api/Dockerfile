# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

WORKDIR /app/services/api

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=180
ENV PIP_RETRIES=10
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ARG TORCH_CPU_VERSION=2.12.0+cpu

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --prefer-binary \
      --index-url https://download.pytorch.org/whl/cpu \
      --extra-index-url https://pypi.org/simple \
      "torch==${TORCH_CPU_VERSION}"
COPY services/api/requirements-runtime.txt /tmp/api-requirements-runtime.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --prefer-binary -r /tmp/api-requirements-runtime.txt
COPY services/api /app/services/api
RUN python -m pip install --no-deps --no-build-isolation /app/services/api

EXPOSE 8000

CMD ["uvicorn", "maintcopilot_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
