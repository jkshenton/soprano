#!/usr/bin/env python


import os
import pickle
import time
import tempfile
from pathlib import Path

import numpy as np

# A "mock" queue submission system to test how well QueueInterface works
# Submission command

mydir = Path(__file__).parent
queue_file = mydir / "queue.pkl"

# For Python3 support
try:
    get_input = raw_input
except NameError:
    get_input = input

try:
    script_first_line = get_input()
except EOFError:
    script_first_line = ""

try:
    with queue_file.open("rb") as qfile:
        joblist = pickle.load(qfile)
except OSError:
    joblist = {}

# Well, add a job with the name of the script's first word
fline_spl = script_first_line.split()
jobname = fline_spl[0]
joblength = float(fline_spl[1])

rnd_id = np.random.randint(100000, 999999)
while rnd_id in joblist:
    rnd_id = np.random.randint(100000, 999999)
rnd_id = str(rnd_id)
joblist[rnd_id] = {"name": jobname, "end": time.time() + joblength}
if len(fline_spl) > 2:
    joblist[rnd_id]["path"] = fline_spl[2]

print(f"Job <{rnd_id}> submitted")

# Use atomic write operation to avoid corruption
with tempfile.NamedTemporaryFile(mode='wb', dir=mydir, delete=False) as tmp_file:
    pickle.dump(joblist, tmp_file)
    tmp_file.flush()
    os.fsync(tmp_file.fileno())
Path(tmp_file.name).replace(queue_file)
