#!/usr/bin/env python


import os
import pickle
import sys
import tempfile
from pathlib import Path

kill_id = sys.argv[1]
mydir = Path(__file__).parent
queue_file = mydir / "queue.pkl"

try:
    with queue_file.open("rb") as qfile:
        joblist = pickle.load(qfile)
    if kill_id not in joblist:
        raise OSError
except OSError:
    sys.exit(f"Job <{kill_id}> not found")

# If it's in joblist, delete it
del joblist[kill_id]
print(f"Job <{kill_id}> has been terminated")

# Use atomic write operation to avoid corruption
if len(joblist) > 0:
    # Write to temporary file first, then move to avoid corruption
    with tempfile.NamedTemporaryFile(mode='wb', dir=mydir, delete=False) as tmp_file:
        pickle.dump(joblist, tmp_file)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
    Path(tmp_file.name).replace(queue_file)
else:
    # Remove the queue file if no jobs left
    queue_file.unlink(missing_ok=True)
