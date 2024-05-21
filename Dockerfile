# hadolint global ignore=DL3007
FROM git.bueraner.de/murdoc/alpine:latest as builder

LABEL org.opencontainers.image.authors="murdoc@storm-clan.de" \
      org.label-schema.name="fritzlog" \
      org.label-schema.vendor="murdoc" \
      org.label-schema.schema-version="1.0.0"

ARG USERNAME="admin"
ARG PASSWORD
ARG URL="https://fritz.box"

ENV FB_USERNAME="$USERNAME"
ENV FB_PASSWORD="$PASSWORD"
ENV FB_URL="$URL"

# renovate: datasource=repology depName=alpine_3_19/py3-pip versioning=loose
ENV PY3_PIP_VERSION="23.3.1-r0"
# renovate: datasource=pypi depName=graypy versioning=loose
ENV GRAYPY_VERSION="2.1.0"
# renovate: datasource=pypi depName=requests versioning=loose
ENV REQUESTS_VERSION="2.32.2"

RUN apk add --update --no-cache \
    py3-pip=="$PY3_PIP_VERSION" \
  && pip install --no-cache-dir --break-system-packages \
    requests=="$REQUESTS_VERSION" \
    graypy=="$GRAYPY_VERSION"

WORKDIR /usr/src/app

COPY . .

CMD ["python", \
     "./fritzlog.py", \
     "-u $FB_USERNAME", \
     "-p $FB_PASSWORD", \
     "-a $FB_URL", \
     "-v"]
