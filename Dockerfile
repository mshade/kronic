FROM python:3.12-alpine AS deps
ENV PYTHONUNBUFFERED=1

RUN apk --no-cache upgrade

COPY requirements.txt /app/

WORKDIR /app
RUN pip install -r requirements.txt


FROM deps AS dev
COPY requirements-dev.txt /app/
RUN pip install -r requirements-dev.txt
RUN apk add --no-cache git openssh-client-default curl
CMD flask run --debug -h 0.0.0.0

# Release image without dev deps
FROM deps AS final
COPY . /app/
RUN addgroup -S kronic && adduser -S kronic -G kronic -u 3000
USER kronic
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0", "--access-logfile=-", "app:app"]
