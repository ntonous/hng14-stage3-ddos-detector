import json
import time

def follow(file_path):
    with open(file_path, "r") as f:
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                time.sleep(0.1)
                continue

            try:
                yield json.loads(line.strip())
            except:
                continue
