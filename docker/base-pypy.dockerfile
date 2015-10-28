FROM pypy:2-2.6-slim

RUN pip install --no-cache-dir virtualenv

COPY ./apt-get-install.sh /
ENV APT_GET_INSTALL=/apt-get-install.sh

RUN virtualenv /appenv && \
    . /appenv/bin/activate
