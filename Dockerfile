FROM python:3.9

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY lib /app/lib
COPY sheets_example.py /app

WORKDIR /app

