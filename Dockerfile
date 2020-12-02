FROM python:3.9.0-alpine3.12
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "cli.py"]

