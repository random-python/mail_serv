"""
Master service:
* setup permissions
* prepare config files
"""

import os
import re
import logging

from mail_serv.command import shell
from mail_serv.support import convert_text2bool
from mail_serv.support import fs_mkdir, fs_chmod, fs_chown , fs_concat, fs_copy
from mail_serv.profiler import profiler_session

logger = logging.getLogger(__name__)
this_dir = os.path.dirname(os.path.abspath(__file__))


def arkon_service():  # runs as root
    logger.info("startup")
    with profiler_session('arkon-service'):
        arkon_tls()
        arkon_tinc()
        arkon_getmail()
        arkon_opendkim()
        arkon_dovecot()
        akron_postfix()
#         arkon_systemd()


def arkon_tls():
    logger.info("setup tls")
    conf = "/etc/tls"
    fs_mkdir(conf)
    fs_chmod(conf, mode=0o640, dir_on=0o550)
    fs_chown(conf, 'root', 'root')


def arkon_tinc():
    logger.info("setup tinc")
    conf = "/etc/tinc"
    tinc = f"{this_dir}/etc/tinc"
    fs_mkdir(conf)
    fs_copy(tinc, conf)
    fs_chmod(conf, dir_off=0o007, file_off=0o007)
    fs_chown(conf, 'root', 'root')


def arkon_getmail():
    logger.info("setup getmail")
    conf = "/etc/getmail"
    fs_mkdir(conf)
    fs_chmod(conf, mode=0o640, dir_on=0o6750)
    fs_chown(conf, 'service', 'service')


def arkon_opendkim():
    logger.info("setup opendkim")
    conf = "/etc/opendkim"
    fs_mkdir(conf)
    fs_chmod(conf, mode=0o640, dir_on=0o6750)
    fs_chown(conf, 'root', 'opendkim')


def arkon_dovecot():
    logger.info("setup dovecot")
    #
    conf = "/etc/dovecot"
    fs_mkdir(conf)
    fs_chmod(conf, mode=0o640, dir_on=0o6750)
    fs_chown(conf, 'root', 'dovecot')
    #
    pipe = "/run/dovecot/syncer"
    fs_mkdir(pipe)
    fs_chmod(pipe, mode=0o660)
    fs_chown(pipe, 'service', 'dovecot')
    #
    data = "/home/data"
    fs_mkdir(data)
    fs_chmod(data, mode=0o660, dir_on=0o6750)
    fs_chown(data, 'service', 'service')
    #
    snap = f"{conf}/conf.snap"  # configuration snapshot
    fs_mkdir(snap)
    os.system(f'doveconf -a > "{snap}/dovecot-settings.conf"')
    os.system(f'doveconf -n > "{snap}/dovecot-override.conf"')
    fs_chmod(snap, mode=0o640, dir_on=0o6750)
    fs_chown(snap, 'root', 'root')


postfix_regex_maps = re.compile(r'^.+[.]maps$')
postfix_regex_main = re.compile(r'^main[.].+[.]conf$')
postfix_regex_master = re.compile(r'^master[.].+[.]conf$')


def postfix_prepare(conf_dir:str) -> None:
    "prepare postfix config: provide include/override/pre-process"
    if not os.path.isdir(conf_dir):
        return
    main_list = list()
    master_list = list()
    for file_name in os.listdir(conf_dir):
        conf_file = f"{conf_dir}/{file_name}"
        if postfix_regex_maps.match(file_name):
            os.system(f"postmap {conf_file}")
        if postfix_regex_main.match(file_name):
            main_list.append(conf_file)
        if postfix_regex_master.match(file_name):
            master_list.append(conf_file)
    main_list.sort()
    master_list.sort()
    fs_concat(f"{conf_dir}/main.cf", main_list)
    fs_concat(f"{conf_dir}/master.cf", master_list)


def akron_postfix():
    logger.info("setup postfix")
    #
    conf = "/etc/postfix"
    fs_mkdir(conf)
    postfix_prepare(conf)
    fs_chmod(conf, mode=0o640, dir_on=0o6750)
    fs_chown(conf, 'root', 'postfix')
    #
    snap = f"{conf}/conf.snap"  # configuration snapshot
    fs_mkdir(snap)
    os.system(f'postconf -f  > "{snap}/postconf-main-settings.conf"')
    os.system(f'postconf -fn > "{snap}/postconf-main-override.conf"')
    os.system(f'postconf -fM > "{snap}/postconf-master.conf"')
    fs_chmod(snap, mode=0o640, dir_on=0o6750)
    fs_chown(snap, 'root', 'root')


def arkon_systemd():  # TODO
    if not convert_text2bool(os.environ.get('ARKON_SYTEMD', 'no')):
        return
    logger.info("setup systemd")
    conf = "/etc/systemd"
    systemd = f"{this_dir}/etc/systemd"
    fs_mkdir(conf)
    fs_copy(systemd, conf)
    fs_chmod(conf, mode=0o555, dir_on=0o6000, file_off=0o111)
    fs_chown(conf, 'root', 'root')
