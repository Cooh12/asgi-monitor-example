FROM python:3.12-slim-bullseye

WORKDIR .

COPY requirements.txt .

RUN apt-get update && apt-get install -y gcc git
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080