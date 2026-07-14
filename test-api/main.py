import os
import signal

from fastapi import FastAPI

app = FastAPI(title="Mock API for Service Monitoring")


@app.get("/")
def root():
    return {"service": "mock-api", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/crash")
def crash():
    os.kill(os.getpid(), signal.SIGTERM)
