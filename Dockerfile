FROM python:3.12-slim-bookworm

WORKDIR /app
COPY . .

ENTRYPOINT ["python", "app.py"]
