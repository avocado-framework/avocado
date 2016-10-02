# This Dockerfile creates an debian image with avocado framework installed
# from source
#
# VERSION 0.1
################
## Usage example:
# git clone github.com/avocado-framework/avocado.git avocado.git
# cd avocado.git
## Make some changes
# patch -p1 < MY_PATCH
## Finally build a docker image
# docker build --force-rm -t debian-avocado-custom -f contrib/docker/Dockerfile.debian .
## Run test inside the docker image
# avocado run --docker fedora-avocado-custom passtest.py
#
FROM debian
MAINTAINER Dmitry Monakhov dmonakhov@openvz.org
# Install and clean in one step to decrease image size

RUN apt-get update && \
    echo install avocado def packages && \
    apt-get install -y --no-install-recommends \
	    git \
	    rsync \
	    make \
	    gdebi-core \
	    pkg-config \
	    libvirt-dev \
	    python-dev \
	    python-lzma \
	    python-pip \
	    python-pystache \
	    python-setuptools \
	    python-stevedore  \
	    python-yaml && \
    echo install extra avocado packages && \
    apt-get install -y --no-install-recommends \
	    ansible \
	    emacs-nox \
	    pigz \
	    libzip2 \
	    pxz && \
    ln -f /usr/bin/pigz  /bin/gzip && \
    ln -f /usr/bin/pigz  /usr/bin/gzip && \
    echo install kernel-devel packages && \
    apt-get install -y --no-install-recommends \
	    build-essential \
	    guilt \
	    bc \
	    flex \
	    bison \
	    libc6-dev \
	    libelf-dev \
	    libnuma-dev \
	    liblzma-dev && \
    echo "Cleanup" && \
    apt-get clean && \
    rm -rf \
       /usr/share/doc /usr/share/doc-base \
       /usr/share/man /usr/share/locale /usr/share/zoneinfo

COPY . /devel/avocado-framework/avocado

RUN cd /devel/avocado-framework/avocado && \
    make requirements && \
    make install && \
    mkdir -p /usr/share/avocado/data/cache && \
    git config --global user.email "avocado@localhost" && \
    git config --global user.name "Avocado tool" && \
    rm -rf /devel/avocado-framework/avocado

