FROM python:2.7-slim

COPY ./apt-get-install.sh /
ENV PKG_INSTALL=/apt-get-install.sh
