FROM python:3.10
MAINTAINER Tom Dryer <tomdryer.com@gmail.com>

RUN useradd --create-home hangups
USER hangups
WORKDIR /home/hangups/

COPY hangups ./hangups
COPY setup.py README.rst ./
RUN pip install --no-cache --user .
RUN mkdir -vp .cache/hangups .config/hangups

VOLUME ["/home/hangups/.config/hangups", "/home/hangups/.cache/hangups"]
ENTRYPOINT [".local/bin/hangups"]
