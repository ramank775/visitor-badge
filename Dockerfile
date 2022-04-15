FROM python:3.10-alpine

ENV host='0.0.0.0'
ENV port=5000
ENV env=prod

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

COPY . /app

RUN dos2unix /app/start.sh

RUN chmod +x /app/start.sh

EXPOSE 5000

ENTRYPOINT [ "/app/start.sh" ]
