FROM debian:buster
WORKDIR /root
RUN apt-get update && apt-get -y install python3 python3-pip
RUN pip3 --no-cache-dir install Flask rpyc aiohttp
RUN adduser --disabled-password --gecos "User" user
RUN mkdir /mnt/data && chmod 0777 /mnt/data
ADD --chown=user:user robodj /home/user/robodj
ENV FLASK_APP=/home/user/robodj STORAGE_PATH=/mnt/data/robodj
CMD ["su", "-c", "flask run --host=0.0.0.0 & rpyc_classic.py & wait", "user"]
