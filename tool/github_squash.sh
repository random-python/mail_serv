# !/usr/bin/env bash

#
# Squash github commits starting from a point
#

point="0a55131d9a16db7f4d29c9c077f485dc7213cc92"
message="Develop"

git reset --soft ${point}
git add --all
git commit --message=${message}
git push --force --follow-tags
