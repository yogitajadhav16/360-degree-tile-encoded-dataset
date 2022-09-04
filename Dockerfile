
FROM ubuntu:20.04

WORKDIR /Dataset
ENV REQUIRED_PACKAGES automake autoconf libtool m4 build-essential git yasm pkgconf
COPY ./input.json /Dataset/input.json
COPY ./encoding.py /Dataset/encoding.py

RUN apt-get update && \
    apt-get install -y python3 && \
    apt-get install -y mediainfo && \
    apt-get install -y ffmpeg && \
    apt-get -y install gpac && \
    apt-get install -y $REQUIRED_PACKAGES && \
    cd /Dataset && \
    git clone https://github.com/ultravideo/kvazaar.git

RUN cd /Dataset/kvazaar && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make install && \
    ldconfig