FROM registry.suse.com/bci/python:3.11

WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "./main.py" ]
