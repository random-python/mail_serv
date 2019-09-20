"""
Dovecot maintenance service
"""

import os
import logging
from mail_serv.profiler import profiler_session
from mail_serv.user import user_list
from mail_serv.tinker import tinker_node_iterate
from mail_serv.maintain import maintain_user
from mail_serv.subscribe import subscribe_user
from mail_serv.replicate import replicate_with_user
from mail_serv.support import report_time, fs_size, fs_strip_eol, fs_mkdir, \
    filesys_session
from mail_serv.config import config_mail_location, config_mail_layout, config_mail_home
from mail_serv.sieve import sieve_persist_mbox_list

logger = logging.getLogger(__name__)


def keeper_service() -> None:
    logger.info(f"startup")
    with profiler_session('keeper-service'):
        keeper_process_all()


def keeper_process_all() -> None:
    logger.debug(f"keep all users")
    for user_name in user_list():
        keeper_process_user(user_name)


@report_time
def keeper_process_user(user_name:str) -> None:
    logger.debug(f"keep single user: {user_name}")
    maintain_user(user_name)
    subscribe_user(user_name)
    keeper_repair_layout(user_name)
    keeper_replicate_node(user_name)
    keeper_report_home_size(user_name)


@report_time
def keeper_report_home_size(user_name:str) -> None:
    "measure disk space in user mail home"
    mail_home = config_mail_home(user_name)
    home_size = fs_size(mail_home)
    logger.debug(f"{user_name}: home_size={home_size:,}")


@report_time
def keeper_repair_layout(user_name:str) -> None:
    "ensure proper mailbox store layout"
    layout_dict = config_mail_layout(user_name)
    TYPE = layout_dict.get('TYPE', None)
    LAYOUT = layout_dict.get('LAYOUT', None)
    DIRNAME = layout_dict.get('DIRNAME', None)
    with filesys_session():
        if TYPE == 'maildir':
            if LAYOUT == 'fs':
                if DIRNAME:
                    keeper_repair_maildir(user_name, DIRNAME)
                else:
                    logger.warning(f"wrong dirname: {DIRNAME}")
            else:
                logger.warning(f"wrong layout: {LAYOUT}")
        else:
            logger.warning(f"wrong type: {TYPE}")


def keeper_repair_maildir(user_name:str, maildir_name:str) -> None:
    "ensure proper mailbox layout for maildir"
    "https://en.wikipedia.org/wiki/Maildir"
    mail_location = config_mail_location(user_name)
    if not os.path.isdir(mail_location):
        logger.warning(f"no mail_location: {mail_location}")
        return
    mbox_list_file = f"{mail_location}/keeper-mbox-list.txt"
    sieve_persist_mbox_list(user_name, mbox_list_file)
    with open(mbox_list_file, "r") as entry_list:
        for entry in entry_list:
            mbox_name = fs_strip_eol(entry)  # relative path
            mbox_path = f"{mail_location}/{mbox_name}"  # absolute path
            maildir_path = f"{mbox_path}/{maildir_name}"  # mail storage dir
            folder_list = [  # layout folders
                f"{maildir_path}/cur",
                f"{maildir_path}/new",
                f"{maildir_path}/tmp",
            ]
            for folder in folder_list:
                fs_mkdir(folder)


@report_time
def keeper_replicate_node(user_name:str) -> None:
    "sync single user"

    @report_time
    def keeper_replicate(node_addr, node_port):
        func_info = f"{user_name} {node_addr}:{node_port}"
        try:
            logger.debug(func_info)
            replicate_with_user(user_name, node_addr, node_port)
        except Exception as error:
            logger.warn(f"failure: {func_info} :: {error}")

    tinker_node_iterate(keeper_replicate)
