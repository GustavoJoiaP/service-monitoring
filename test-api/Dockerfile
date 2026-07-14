FROM docker.io/library/python:3.11-alpine

RUN pip install --no-cache-dir fastapi uvicorn

COPY main.py /app/main.py

WORKDIR /app

EXPOSE 3000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
