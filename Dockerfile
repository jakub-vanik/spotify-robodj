FROM debian:testing
RUN apt-get update && apt-get -y install python3 python3-aiohttp python3-flask python3-flask-babel python3-rpyc python3-werkzeug
RUN useradd -m user && mkdir /mnt/data && chmod 0777 /mnt/data
ADD --chown=user:user robodj /home/user/robodj
CMD ["su", "-c", "FLASK_APP=/home/user/robodj flask run --host=0.0.0.0 & STORAGE_PATH=/mnt/data/robodj rpyc_classic & wait", "user"]
