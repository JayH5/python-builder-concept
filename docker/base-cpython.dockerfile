FROM python:2.7-slim

COPY ./apt-get-install.sh /
ENV APT_GET_INSTALL=/apt-get-install.sh

RUN virtualenv /appenv && \
    . /appenv/bin/activate
