import time

counter = 0

print("Consumer Worker started.")

while True:

    counter += 1

    print(f"[CONSUMER] Waiting message {counter}")

    time.sleep(2)