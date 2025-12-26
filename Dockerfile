# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /opt/wikidot-translate

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

ENV PYTHONPATH $WORKDIR:$PYTHONPATH
ENV PYTHONUNBUFFERED True


#After you create the image, you can now build it. Use the following command to build it:
#$ docker build --tag python-docker
