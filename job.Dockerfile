FROM registry.suse.com/bci/python:3.11

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

CMD [ "python3", "./job.py" ]
