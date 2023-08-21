FROM python:3.11-alpine

RUN apk add --no-cache curl

COPY requirements.py /app/

WORKDIR /app
RUN pip install -r requirements.py