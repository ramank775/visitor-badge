#! /bin/sh
if [ $env == "prod" ] 
then
gunicorn -b "$host:$port" main:app --log-file -
else
python3 main.py
fi