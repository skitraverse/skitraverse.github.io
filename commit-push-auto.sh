#!/bin/bash -x

source venv/bin/activate

python app.py freeze

deactivate


newfiles=$(git status -s | sed  '/^??/!d; /conflict/d; / .#/d; s/^?? //g')
modfiles=$(git status -s | sed  '/^ M/!d; s/^ M //g')


if [[ $# -eq 0 ]]; then
    msg="uploaded new content $(date -u +%F-%R)"
else
    msg=$*
fi

if [[ -n $newfiles ]] || [[-n $modfiles ]]; then
    git add $newfiles $modfiles
    git commit . -m "$msg" && git push origin main
fi

