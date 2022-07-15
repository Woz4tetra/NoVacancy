FROM python:3.9

COPY web/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY web/src /app
COPY lib/ /app/lib/


WORKDIR /app

CMD [ "flask", "run", "--host=0.0.0.0"]