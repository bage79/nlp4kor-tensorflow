#!/usr/bin/env bash
PROGRAM="text_preprocess.py"
PROJECT_DIR=${HOME}'/workspace/nlp4kor_tensorflow'

git --work-tree=${PROJECT_DIR} --git-dir=${PROJECT_DIR}/.git pull

echo "pkill -f ${PROGRAM}"
pkill -f ${PROGRAM}

echo "rm -f logs/${PROGRAM}.*"
rm -f logs/${PROGRAM}.*

echo "python3 ./${PROGRAM} >/dev/null 2>&1 &"
nohup python3 ./${PROGRAM} >/dev/null 2>&1 &
