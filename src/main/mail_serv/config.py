"""
Extract configuration entries
"""

import logging
from mail_serv.command import doveconf
from typing import Mapping

logger = logging.getLogger(__name__)


def config_doveadm_password() -> str:
    "shared client/server secret"
    return doveconf('-h', 'doveadm_password')


def config_client_ca_file() -> str:
    "client connection certificate"
    return doveconf('-h', 'ssl_client_ca_file')


def config_doveadm_port() -> str:
    "remote server administration port"
    return doveconf('-h', 'doveadm_port')


def config_mail_home(user_name:str) -> str:
    """
    discover absolute user home dir
    user_name: person@domain
    mail_home: /home/data/%d/%n
    """
    assert '@' in user_name, f'need "@" in user_name: {user_name}'
    mail_home = doveconf('-h', 'mail_home')
    assert mail_home, f"wrong mail_home: {mail_home}"
    assert '%n' in mail_home, f'need "%n" in mail_home: {mail_home}'
    assert '%d' in mail_home, f'need "%d" in mail_home: {mail_home}'
    user_term = user_name.split('@')
    person = user_term[0]
    domain = user_term[1]
    mail_home = mail_home.replace('%n', person)
    mail_home = mail_home.replace('%d', domain)
    return mail_home


def config_mail_location(user_name:str) -> str:
    """
    discover absolute user mail dir
    user_name: person@domain
    mail_location: sdbox:~/mail:key=val
    mail_location: maildir:~/mail:LAYOUT=fs:DIRNAME=_m_a_i_l_
    """
    assert '@' in user_name, f'need "@" in user_name: {user_name}'
    mail_home = config_mail_home(user_name)
    mail_location = doveconf('-h', 'mail_location')
    assert mail_location, f'wrong mail_location: {mail_location}'
    assert ':' in mail_location, f'need ":" in mail_location: {mail_location}'
    assert '~' in mail_location, f'need "~" in mail_location: {mail_location}'
    location_term = mail_location.split(':')  # split all
    location_type = location_term[0]  # mail box type
    location_path = location_term[1]  # relative path
    location_result = location_path.replace('~', mail_home)  # convert to absolute
    return location_result


def config_mail_layout(user_name:str) -> Mapping[str, str]:
    "extract mail location configuration parameters: TYPE, PATH, LAYOUT, DIRNAME"
    mail_location = doveconf('-h', 'mail_location')
    layout_dict = dict()
    if not mail_location:
        logger.warning(f"missing mail_location: {mail_location}")
        return layout_dict
    if not ':' in mail_location:
        logger.warning(f"wrong format mail_location: {mail_location}")
        return layout_dict
    location_term = mail_location.split(':')  # split all
    if not len(location_term) >= 3:
        logger.warning(f"short format mail_location: {mail_location}")
        return layout_dict
    layout_dict['TYPE'] = location_term[0]  # mail box type
    layout_dict['PATH'] = location_term[1]  # mail box path
    for entry in location_term[2:]:
        if '=' in entry:
            entry_term = entry.split('=')
            key = entry_term[0]
            value = entry_term[1]
        else:  # key-only entry
            key = entry
            value = "true"
        layout_dict[key] = value

    return layout_dict


def config_any_home(user_name:str, entry_name:str) -> str:
    """
    discover absolute path in user home
    """
    assert '@' in user_name, f'need "@" in user_name: {user_name}'
    mail_home = config_mail_home(user_name)
    config_entry = doveconf('-h', entry_name)
    assert '~' in config_entry, f'need "~" in config_entry: {config_entry}'
    config_path = config_entry.replace('~', mail_home)
    return config_path


def config_sieve_path(user_name:str) -> str:
    """
    discover absolute sieve dir
    user_name: person@domain
    plugin/sieve_dir: '~/sieve'
    """
    return config_any_home(user_name, 'plugin/sieve_dir')


def config_sieve_active(user_name:str) -> str:
    """
    discover absolute sieve.active file
    user_name: person@domain
    plugin/sieve: '~/active.sieve'
    """
    return config_any_home(user_name, 'plugin/sieve')


def config_sieve_default(user_name:str) -> str:
    """
    user_name: person@domain
    plugin/sieve_default: '~/active.sieve'
    """
    return config_any_home(user_name, 'plugin/sieve_default')


def config_syncer_dir(user_name:str) -> str:
    """
    user_name: person@domain
    plugin/syncer_dir: '~/syncer'
    """
    return config_any_home(user_name, 'plugin/syncer_dir')


def config_syncer_pipe() -> str:
    """
    extract '/run/dovecot/syncer/pipe'
    """
    return doveconf('-h', 'plugin/syncer_pipe')
