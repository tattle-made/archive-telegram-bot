FROM python:3.8.1-alpine3.11
RUN apk add gcc
RUN apk add linux-headers
RUN apk add --update alpine-sdk
RUN apk add libffi-dev
RUN apk add openssl-dev
COPY . /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1 
RUN pip install -r requirements.txt
EXPOSE 8443 
# RUN apk add gcc
# RUN pip3 install scrapy
CMD python3 prototype.py