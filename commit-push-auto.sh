#!/bin/bash -x

source venv/bin/activate

python app.py freeze

deactivate

git add events/* info/* content/*

if [[ $# -eq 0 ]]; then
    msg="uploaded new content $(date -u +%F-%R)"
else
    msg=$*
fi

git commit . -m "$msg" && git push origin master
