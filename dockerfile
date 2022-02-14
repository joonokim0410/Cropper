# docker build -t pixtree/pillar_detection .
# docker run -it --name jhkim_pillar_detection --shm-size=60G -w /app -v /mnt/DataSet:/DataSet pixtree/pillar_detection:latest bash
# python pillar_detection.py -i /DataSet/Pixtree-NDA/SME/20220114_01주차/input/SMTOWN/ -c 0

FROM python:3.8.12-buster

LABEL name="PillarDetection"
LABEL date="2022-01-11"

RUN mkdir /app/
WORKDIR /app/

COPY pillar_detection.py /app/
COPY pillar_detection_core.py /app/
COPY pillar_detection_utils.py /app/
COPY requirements.txt /app/

RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get dist-upgrade -y \
    && apt-get install -y \
    ffmpeg

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt