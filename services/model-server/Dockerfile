# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

WORKDIR /app

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
COPY requirements-runtime.txt /tmp/model-server-requirements-runtime.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --prefer-binary -r /tmp/model-server-requirements-runtime.txt
COPY . .
RUN python -m pip install --no-deps --no-build-isolation .

EXPOSE 8001

CMD ["uvicorn", "maintcopilot_model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
