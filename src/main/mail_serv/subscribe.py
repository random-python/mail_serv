"""
Mailbox subscription operations

https://wiki2.dovecot.org/Tools/Doveadm/Mailbox
"""

import os
import  logging

from mail_serv.command import shell
from mail_serv.config import config_mail_location
from mail_serv.support import report_time

logger = logging.getLogger(__name__)


@report_time
def subscribe_user(user_name:str) -> None:
    "enforce complete subscriptions"

    # per-user mail store
    mail_location = config_mail_location(user_name)

    if not os.path.isdir(mail_location):
        logger.warning(f"no mail_location: {mail_location}")
        return

    # dovecot subscriptions configuration file
    dovecot_subs = f"{mail_location}/subscriptions"
    # temporary copy file for atomic update operation
    working_subs = f"{mail_location}/subscriptions.work"

    # generate dovecot subscriptions file
    shell(f"""
        doveadm mailbox list -u "{user_name}" | tee "{working_subs}"
        chown service:service "{working_subs}"
        mv -f "{working_subs}" "{dovecot_subs}"
    """)
