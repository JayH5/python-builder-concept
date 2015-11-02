FROM ubuntu:14.04

COPY ./apt-get-install.sh /
ENV APT_GET_INSTALL=/apt-get-install.sh

RUN $APT_GET_INSTALL python2.7 python

RUN set -x \
    && $APT_GET_INSTALL bzip2 curl ca-certificates \
    && curl -SL 'https://bootstrap.pypa.io/get-pip.py' | python \
    && apt-get purge -y --auto-remove bzip2 curl ca-certificates \
    && rm -rf ${HOME}/.cache/pip

RUN pip install --no-cache-dir virtualenv
RUN virtualenv /appenv && \
    . /appenv/bin/activate
