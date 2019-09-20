"""
User support operations:
user can configure server-side doveadm actions
via configuration stored as magic sieve file
* https://wiki2.dovecot.org/Tools/Doveadm/Move
* https://wiki2.dovecot.org/Tools/Doveadm/Flags
* https://wiki2.dovecot.org/Tools/Doveadm/Expunge
* https://wiki2.dovecot.org/Tools/Doveadm/Deduplicate
"""

import re
import shlex
import logging
from typing import List, Callable
from mail_serv.command import doveadm
from mail_serv.user import user_list
from mail_serv.support import report_time

logger = logging.getLogger(__name__)

# note: config entries look like sieve comments
maintain_regex_move = re.compile(r'^#move#(.+)$')
maintain_regex_expunge = re.compile(r'^#expunge#(.+)$')
maintain_regex_flags_add = re.compile(r'^#flags-add#(.+)$')
maintain_regex_flags_rem = re.compile(r'^#flags-rem#(.+)$')
maintain_regex_deduplicate = re.compile(r'^#deduplicate#(.+)$')

# supported config entries
maintain_regex_map = dict([
    # doveadm action -> regex matcher
    ('move', maintain_regex_move),
    ('expunge', maintain_regex_expunge),
    ('flags add', maintain_regex_flags_add),
    ('flags remove', maintain_regex_flags_rem),
    ('deduplicate -m', maintain_regex_deduplicate),  # '-m' : match by message-id
])


def maintain_all() -> None:
    for user in user_list():
        maintain_user(user)


def maintain_conf_list(
        user_name:str,
        # user sieve config entry name
        conf_name:str="A_R_K_O_N.maintain",
    ) -> List[str]:
    "load configuration from magic sieve user_name entry"
    conf_list = list()
    try:
        conf_text = doveadm('sieve' , 'get', '-u', user_name, conf_name)
        conf_list = conf_text.splitlines()
    except Exception as error:
        logger.warn(f"conf list failure: {error}")
    return conf_list


def maintain_apply(user_name:str, action:str, search:str) -> None:
    "apply user mailbox modifications"
    command = maintain_command(user_name, action, search)
    try:
        logger.debug(f"command: {command}")
        doveadm(*command)
    except Exception as error:
        logger.warn(f"failure: {command} :: {error}")


@report_time
def maintain_user(user_name:str, apply_func:Callable=maintain_apply) -> None:
    "update user mailbox based on sieve search entry"

    entry_list = maintain_conf_list(user_name)

    for entry in entry_list:
        for action, matcher in maintain_regex_map.items() :
            match = matcher.match(entry)
            if match:
                search = match.group(1)
                apply_func(user_name, action, search)


def maintain_command(user_name:str, action:str, search:str) -> List[str]:
    "produce doveadm maintenance command options"
    action_opts = action.strip().split(' ')  # provide doveadm verb and opts
    search_opts = shlex.split(search.strip())  # provide doveadm search_query
    command = action_opts + ['-u', user_name] + search_opts
    return command
