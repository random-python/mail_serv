"""
Dovecot mailbox synchronization operations

https://wiki2.dovecot.org/Tools/Doveadm/Sync
-N    Synchronize all the available namespaces
-l secs    Lock the dsync for this user. Wait for maximum secs before giving up.
-u user/mask    Run the command only for the given user.
-m mailbox    Synchronize only this mailbox name
-g mailbox_guid    Synchronize only this mailbox guid
destination    tcp:host[:port] Connects to remote doveadm server via TCP
"""

import os
import logging
from typing import List
from mail_serv.config import config_doveadm_port
from mail_serv.command import doveadm

logger = logging.getLogger(__name__)


def replication_list(host_list:List[str]) -> List[str] :
    "find active server host list"
    port = config_doveadm_port()
    live_list = []
    timeout = 3
    for host in host_list:
        rv = os.system(f"netcat --tcp --zero --wait={timeout} {host} {port}")
        if rv == 0:
            live_list.append(host)
    return live_list


def replicate_lock_time(lock_time:int=3) -> str:
    "discover replication lock timeout"
    return str(os.environ.get('REPLICATE_LOCK_TIME', lock_time))


def replicate_protocol(protocol:str='tcp') -> str:
    "discover replication protocol"
    return os.environ.get('REPLICATE_PROTOCOL', protocol)


def replicate_destination(addr:str, port:str) -> str:
    "replication desination location"
    protocol = replicate_protocol()
    destination = f"{protocol}:{addr}:{port}"
    return destination


def replicate_with_user(user:str, addr:str, port:str) -> None:
    "replicate all out-of-sync mailboxes for the user"
    lock_time = replicate_lock_time()
    destination = replicate_destination(addr, port)
    doveadm('sync', '-N', '-l', lock_time, '-u', user, '-m', '*', destination)


def replicate_with_mbox(user:str, mbox:str, addr:str, port:str) -> None:
    "replicate single mailbox for the user, selected by mailbox name"
    lock_time = replicate_lock_time()
    destination = replicate_destination(addr, port)
    doveadm('sync', '-N', '-l', lock_time, '-u', user, '-m', mbox, destination)


def replicate_with_guid(user:str, guid:str, addr:str, port:str) -> None:
    "replicate single mailbox for the user, selected by mailbox guid"
    lock_time = replicate_lock_time()
    destination = replicate_destination(addr, port)
    doveadm('sync', '-N', '-l', lock_time, '-u', user, '-g', guid, destination)
