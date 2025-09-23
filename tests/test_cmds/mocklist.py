#!/usr/bin/env python


import os
import pickle
import sys
import time
import tempfile
from pathlib import Path

# A "mock" queue submission system to test how well QueueInterface works
# Listing command

mydir = Path(__file__).parent
queue_file = mydir / "queue.pkl"

try:
    with queue_file.open("rb") as qfile:
        joblist = pickle.load(qfile)
    if len(joblist) == 0:
        raise OSError
except OSError:
    sys.exit("No unfinished jobs found")

# Check if any jobs are finished and in case remove them
joblist_updated = {}
for job in joblist:
    print("{0} => {1}".format(joblist[job]["end"], time.time()))
    if joblist[job]["end"] > time.time():
        joblist_updated[job] = joblist[job]
    elif "path" in joblist[job]:
        output_file = Path(joblist[job]["path"]) / f"{joblist[job]['name']}.castep"
        output_file.write_text("Fake CASTEP")

joblist = joblist_updated

for job in joblist:
    print(
        ("{0}\tusername\tRUN\tqueuename\tnodeURL\t{1}" "\tMM DD HH:MM").format(
            job, joblist[job]["name"]
        )
    )

# Use atomic write operation to avoid corruption
if len(joblist) > 0:
    with tempfile.NamedTemporaryFile(mode='wb', dir=mydir, delete=False) as tmp_file:
        pickle.dump(joblist, tmp_file)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
    Path(tmp_file.name).replace(queue_file)
else:
    # Remove the queue file if no jobs left
    queue_file.unlink(missing_ok=True)
