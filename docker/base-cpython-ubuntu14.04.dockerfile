FROM ubuntu:14.04

COPY ./apt-get-install.sh /
ENV PKG_INSTALL=/apt-get-install.sh

RUN $PKG_INSTALL python

RUN set -x \
    && $PKG_INSTALL ca-certificates curl \
    && curl -SL 'https://bootstrap.pypa.io/get-pip.py' | python \
    && apt-get purge -y --auto-remove ca-certificates curl \
    && rm -rf ${HOME}/.cache/pip
