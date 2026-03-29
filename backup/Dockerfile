FROM redis:alpine

RUN apk add --no-cache bash

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

# Run backup every hour
RUN echo '0 * * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1' \
    | crontab -

CMD ["crond", "-f", "-l", "2"]
