FROM ubuntu:14.04

COPY ./apt-get-install.sh /
ENV PKG_INSTALL=/apt-get-install.sh

RUN echo "deb http://ppa.launchpad.net/pypy/ppa/ubuntu trusty main" | tee /etc/apt/sources.list.d/pypy-ppa.list && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 2862D0785AFACD8C65B23DB0251104D968854915 && \
    $PKG_INSTALL pypy && \
    ln -s $(which pypy) /usr/local/bin/python

RUN set -x \
    && $PKG_INSTALL ca-certificates curl \
    && curl -SL 'https://bootstrap.pypa.io/get-pip.py' | python \
    && apt-get purge -y --auto-remove ca-certificates curl \
    && rm -rf ${HOME}/.cache/pip
