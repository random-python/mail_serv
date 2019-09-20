"""
Dovecot command wrapper
"""

import os
import logging
import subprocess
from typing import List, Tuple
from mail_serv.process import execute_process_sert

logger = logging.getLogger(__name__)


def execute_dove(dove_cmd:str, *option_list:Tuple[str]):
    config_file = os.getenv('DOVECOT_CONFIG', '/etc/dovecot/dovecot.conf')
    command = [dove_cmd, '-c', config_file] + list(option_list)
    return execute_process_sert(command).strip()


def doveconf(*option_list:Tuple[str]):
    return execute_dove('doveconf', *option_list)


def doveadm(*option_list:Tuple[str]):
    return execute_dove('doveadm', *option_list)


def sieve_filter(*option_list:Tuple[str]):
    return execute_dove('sieve-filter', *option_list)


def shell(script) -> subprocess.CompletedProcess:
    return subprocess.check_output(script, shell=True)
