FROM python:3.4
MAINTAINER Tom Dryer <tomdryer.com@gmail.com>

WORKDIR /opt/hangups
COPY hangups ./hangups
COPY setup.py README.rst ./
RUN python setup.py install
VOLUME ["/root/.config/hangups", "/root/.cache/hangups"]
ENTRYPOINT ["hangups"]
