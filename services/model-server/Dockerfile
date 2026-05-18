FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8001

CMD ["uvicorn", "maintcopilot_model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
