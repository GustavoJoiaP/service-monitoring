import time

counter = 0

print("Producer Worker started.")

while True:

    counter += 1

    print(f"[PRODUCER] Producing message {counter}")

    time.sleep(1)