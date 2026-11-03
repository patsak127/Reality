#!/bin/sh
cd /workspace/reality/mutation-v4
for f in keys sorts exact __main__ syntax readers bids101 kernel witness; do
  echo "start $f $(date +%T)" >> logs/batch.progress
  if [ "$f" = keys ]; then ./run.sh src/reality4/$f.py; else ./run.sh src/reality4/$f.py --reuse-coverage; fi
  echo "end $f exit $? $(date +%T)" >> logs/batch.progress
done
echo "start machine nocov $(date +%T)" >> logs/batch.progress
./run.sh src/reality4/machine.py --no-coverage
echo "end machine exit $? $(date +%T)" >> logs/batch.progress
echo "all done $(date +%T)" >> logs/batch.progress
