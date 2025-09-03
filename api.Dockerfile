FROM registry.suse.com/bci/python:3.11

WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "api:app"]
