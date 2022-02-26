
import os
import time
import threading
from mail_serv_test import *
from mail_serv.filer import *

import inotify.adapters
from mail_serv.support import fs_mkdir


def test_notify():
    print()

    fs_mkdir('/tmp/notify')

    notify = inotify.adapters.InotifyTree('/tmp/notify')

    for index in range(3):
        with open(f'/tmp/notify/test-file-{index}', 'w'):
            pass

    event_list = notify.event_gen(yield_nones=False, timeout_s=1)

    event_list = list(event_list)

    for event in event_list:
        print(event)

    time.sleep(1)


def test_file_sync():
    print()
