"""
Dovecot user operations
"""

import logging
from typing import List
from mail_serv.command import doveadm

logger = logging.getLogger(__name__)


def user_list() -> List[str]:
    "extract users from dovecot"
    user_text = doveadm('user', '-u', '*')
    user_list = user_text.splitlines()
    return user_list


def user_path(user_name:str) -> str:
    "convert: akron@private.dom -> private.dom/akron"
    assert user_name, f"wrong user_name: {user_name}"
    assert '@' in user_name, f'need "@" in user_name: {user_name}'
    user_term = user_name.split('@')
    return f"{user_term[1]}/{user_term[0]}"
