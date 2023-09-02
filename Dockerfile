FROM python:3.11-alpine as deps

RUN apk add --no-cache curl

COPY requirements.py /app/

WORKDIR /app
RUN pip install -r requirements.py


FROM deps as dev
CMD flask run --debug -h 0.0.0.0
