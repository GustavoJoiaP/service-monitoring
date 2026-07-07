import signal
import sys
import time

running = True


def shutdown(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

counter = 0

print("Worker process started.")

while running:

    counter += 1

    print(f"Worker running... {counter}")

    time.sleep(2)

print("Worker stopped.")

sys.exit(0)