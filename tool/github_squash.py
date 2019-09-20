#!/usr/bin/env python

"""
Squash github commits starting from a point
"""

from devrepo import shell

point = "0a55131d9a16db7f4d29c9c077f485dc7213cc92"
message = "Develop"

shell(f"git reset --soft {point}")
shell(f"git add --all")
shell(f"git commit --message='{message}'")
shell(f"git push --force --follow-tags")
