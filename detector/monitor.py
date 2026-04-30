import time
import os
import json


def follow(filename):
    while not os.path.exists(filename):
        time.sleep(1)

    with open(filename, "r") as f:
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                time.sleep(0.2)
                continue

            try:
                yield json.loads(line.strip())
            except:
                continue
