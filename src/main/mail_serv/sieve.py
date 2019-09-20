"""
Sieve filter build and apply operations

https://support.tigertech.net/sieve
http://pigeonhole.dovecot.org/doc/man1/sieve-filter.1.html
http://www.gyford.com/phil/writing/2010/07/02/sieve-filters.php
"""

import os
import re
import logging
from mail_serv.user import user_list
from mail_serv.config import config_sieve_active, config_sieve_path
from mail_serv.command import sieve_filter, shell
from mail_serv.support import fs_strip_eol, fs_rmany, fs_mkdir

logger = logging.getLogger(__name__)


def sieve_suffix() -> str:
    return "sieve"


def sieve_system_name(name:str) -> str:
    "name of system-generated sieve filter for a mailbox"
    return f"{name}.system"


def sieve_system_file(base_dir:str, name:str) -> str:
    "location of sieve system-generated filter for a mailbox"
    system_name = sieve_system_name(name)
    return f"{base_dir}/{system_name}.{sieve_suffix()}"


def sieve_invoke_all() -> None:
    "apply sieve filters for all users"
    for user in user_list():
        sieve_invoke_user(user)


def sieve_invoke_user(user:str, mbox:str='INBOX') -> None:
    "apply sieve filters for single user"
    script = config_sieve_active(user)
    if os.path.isfile(script):
        logger.debug(f"sieve filter: {user} {script}")
        sieve_filter('-e', '-W', '-u', user, script, mbox)
    else:
        logger.debug(f"sieve filter: {user} no-active-script")


# match base mailbox
# example: Vendor
# group(1) = Vendor # base_mbox
sieve_regex_base = re.compile(
    r'^([^/]+)$',
    re.RegexFlag.IGNORECASE,
)

# match mailbox with filter definition
# example: Vendor/Company/First Last [keyword] first.last@company.com
# group(1) = Vendor # base_mbox
# group(2) = [keyword] # define_subj
# group(3) = first.last@company.com # define_addr
sieve_regex_define = re.compile(
    r'^([^/]+)/[^][]*[ ]*(\[[^/]+\])?[ ]+([^/ ]*@[^/ ]+)$',
    re.RegexFlag.IGNORECASE,
)


def sieve_build_all() -> None:
    "build sieve filters for all users"
    for user_name in user_list():
        sieve_build_user(user_name)


def sieve_arkon() -> str:
    "root sieve script name, must not interfere with any user mailbox names"
    return os.environ.get('SIEVE_ARKON', 'A_R_K_O_N')


def sieve_build_user(user_name:str) -> None:
    "build sieve filters for single user"

    logger.debug(f"sieve build: {user_name}")

    sieve_dir = config_sieve_path(user_name)
    build_dir = f"{sieve_dir}/sys"

    # ensure build folder
    fs_rmany(build_dir)
    fs_mkdir(build_dir)

    # persist user mailbox list
    mailbox_list = f"{build_dir}/a_mailbox_list.txt"
    sieve_persist_mbox_list(user_name, mailbox_list)

    # collect base mailbox list
    include_list = f"{build_dir}/a_include_list.txt"

    # sieve root script
    arkon = sieve_arkon()
    arkon_name = sieve_system_name(arkon)
    arkon_file = sieve_system_file(build_dir, arkon)

    # create filter tree
    with open(arkon_file, "w") as arkon_text, open(include_list, "w") as include_text:
        arkon_text.write(f'# {arkon_name}\n')
        arkon_text.write(f'require "include";\n')

        # create base filters
        with open(mailbox_list, "r") as entry_list:
            for entry in entry_list:
                mbox_path = fs_strip_eol(entry)
                match_root = sieve_regex_base.match(mbox_path)
                if match_root:
                    base_mbox = match_root.group(1)
                    base_name = sieve_system_name(base_mbox)
                    base_file = sieve_system_file(build_dir, base_mbox)
                    # arkon uses base script
                    arkon_text.write(f'include :personal "{base_name}";\n')
                    # setup initial base script
                    with open(base_file, "w") as script:  # create
                        script.write(f'# {base_name}\n')
                        script.write(f'require "fileinto";\n')
                    # remember base filters
                    include_text.write(f'{base_mbox}\n')

        # populate base filters
        with open(mailbox_list, "r") as entry_list:
            for entry in entry_list:
                mbox_path = fs_strip_eol(entry)
                match_define = sieve_regex_define.match(mbox_path)
                if match_define:
                    base_mbox = match_define.group(1)
                    base_name = sieve_system_name(base_mbox)
                    base_file = sieve_system_file(build_dir, base_mbox)
                    define_subj = match_define.group(2)
                    define_addr = match_define.group(3)
                    if define_subj:
                        define_subj = define_subj[1:-1]  # remove []
                    # provide filter expression
                    sieve_code = sieve_code_entry(define_subj, define_addr, mbox_path)
                    with open(base_file, "a") as script:  # append
                        script.write(f"{sieve_code}\n")

    # activate generated filters
    with open(include_list, "r") as entry_list:
        for entry in entry_list:
            base_mbox = fs_strip_eol(entry)
            base_name = sieve_system_name(base_mbox)
            base_file = sieve_system_file(build_dir, base_mbox)
            sieve_persist_filter(user_name, base_name, base_file)

    sieve_persist_filter(user_name, arkon_name, arkon_file)


def sieve_persist_mbox_list(user_name:str, mbox_list_file:str) -> None:
    "extract sorted list of mail boxes for a user"
    shell(
        f'doveadm mailbox list -u "{user_name}" | sort -V | uniq | tee "{mbox_list_file}"'
    )


def sieve_persist_filter(user_name:str, filter_name:str, filter_file:str) -> None:
    "inject sieve file into dovecot"
    shell(
        f'cat "{filter_file}" | doveadm sieve put -u "{user_name}" "{filter_name}"'
    )


def sieve_code_entry(define_subj:str, define_addr:str, mbox_path:str) -> str:
    "generate sieve filter code snippet based on subject/address"
    # match <name@domain> field in these headers
    test_addr = f'address :contains [ "To", "CC", "From", "Sender", "Reply-To" ] "{define_addr}"'
    body_file = f'{{ fileinto "{mbox_path}"; stop; }}'
    if define_subj :
        # match [subject] string in these headers
        test_subj = f'header :contains [ "From", "Subject" ] "{define_subj}"'
        return f"if allof( {test_addr} , {test_subj} ) {body_file}"
    else :
        return f"if {test_addr} {body_file}"
