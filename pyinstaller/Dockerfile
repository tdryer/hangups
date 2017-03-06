# CentOS 6 (for glibc forward-compatibility) with Python 3.5 and PyInstaller

FROM centos:6
MAINTAINER Tom Dryer <tomdryer.com@gmail.com>

RUN yum install -y curl gcc make openssl-devel

RUN curl -LO https://www.python.org/ftp/python/3.5.3/Python-3.5.3.tgz && \
    tar -xzf Python-3.5.3.tgz && \
    cd Python-3.5.3 && \
    ./configure --enable-shared --enable-ipv6 --enable-optimizations && \
    make && \
    make install && \
    cd .. && \
    rm -rf Python-3.5.3 Python-3.5.3.tgz

ENV LD_LIBRARY_PATH /usr/local/lib

RUN /usr/local/bin/pip3 install pyinstaller
