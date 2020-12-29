FROM alpine:latest
MAINTAINER Dzmitry Stremkouski mitroko@gmail.com

ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 python2
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools youtube-dl
COPY cli2dlna.py /usr/bin/cli2dlna.py
RUN chmod 0755 /usr/bin/cli2dlna.py
RUN sed -i "s|^ytd.*|ytd = os.getenv('YOUTUBE_DL', '/usr/bin/youtube-dl')|; s|^rconf.*|rconf = '/renderer.cache'|" /usr/bin/cli2dlna.py
VOLUME ["/renderer.cache"]
ENTRYPOINT ["/usr/bin/cli2dlna.py"]
