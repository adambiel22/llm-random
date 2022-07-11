import os
import sys
import datetime

template = """#!/bin/bash
#
#SBATCH --job-name=lizard_train{JOB_ID}
#SBATCH --partition=common
#SBATCH --qos=16gpu3d
#SBATCH --gres=gpu:rtx2080ti:1
#SBATCH --time=0-05:00:00
#SBATCH --output=/home/sj359674/logs/t{TIMESTAMP}/sbatchlogs{JOB_ID}.txt

source venv/bin/activate
python3 initbert_train.py {ARGS}
"""

SLEEPTIME = 3

# create a directory name based on timestamp
timestamp = datetime.datetime.now().strftime("%m_%d_%H_%M_%S")

# create a directory for the logs
log_dir = 'logs/t' + timestamp
print('log_dir:', log_dir)
os.makedirs('/home/sj359674/' + log_dir)

jobs = []
REAL_RUN = None

for lr in [0.003, 0.001, 0.0003, 0.0001, 0.00003]:
    jobs.append((f'LEARNING_RATE={lr}', 'STANDARD'))

for lr in [0.003, 0.001, 0.0003, 0.0001, 0.00003]:
    jobs.append((f'LEARNING_RATE={lr}', 'FIXED'))

PREFIX = None


REMOVEAFTER = False

for arg in sys.argv[1:]:
    if arg.startswith('--prefix='):
        PREFIX = arg[arg.index('=')+1:]
    elif arg.startswith('--real'):
        REAL_RUN = True
    elif arg.startswith('--test'):
        REAL_RUN = False
    elif arg.startswith('--removeafter'):
        REMOVEAFTER = True
    elif arg.startswith('--sleep='):
        SLEEPTIME = int(arg[arg.index('=')+1:])
    else:
        print(f'Unknown argument: {arg}')
        sys.exit(1)

if PREFIX is None:
    raise ValueError('--prefix=<prefix> is required')
if REAL_RUN is None:
    raise ValueError('--real or --test is required')


CLEARMLDIR = f"jaszczur/init/batched/{PREFIX}"

# make directory named "train_scripts"
train_scripts_dir = 'train_scripts'
if not os.path.exists(train_scripts_dir):
    os.makedirs(train_scripts_dir)

# remove files from 'train_scripts' directory
for f in os.listdir(train_scripts_dir):
    os.remove(os.path.join(train_scripts_dir, f))

for job_id, job in enumerate(jobs):
    job_id = f'{PREFIX}{job_id}'
    args = ' '.join(job) + f' CLEARMLDIR={CLEARMLDIR}'
    filetext = template.format(JOB_ID=job_id, ARGS=args, TIMESTAMP=timestamp)
    with open(f'{train_scripts_dir}/train{job_id}.sh', 'w') as f:
        f.write(filetext)

# run all scripts in 'train_scripts' directory
for f in os.listdir(train_scripts_dir):
    if REAL_RUN:
        # sleep for 3 secs
        os.system(f'sleep {SLEEPTIME}')
        os.system(f'sbatch {train_scripts_dir}/{f}')
    else:
        print(f'Would run: sbatch {train_scripts_dir}/{f}')
    print(f'Submitted {f}')

if REMOVEAFTER:
    # remove files from 'train_scripts' directory and directory itself
    for f in os.listdir(train_scripts_dir):
        os.remove(os.path.join(train_scripts_dir, f))
    os.rmdir(train_scripts_dir)
    print(f'Removed {train_scripts_dir}')