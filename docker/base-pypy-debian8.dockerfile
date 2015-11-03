FROM pypy:2-2.6-slim

COPY ./apt-get-install.sh /
ENV PKG_INSTALL=/apt-get-install.sh
