
import os
import time
import threading
from mail_serv_test import *
from mail_serv.procname import *
from mail_serv.command import shell


def test_thread_name():
    print()

    thread_name = 'hello-kitty-0123456789'

    def dummy_target():
        procname_set(threading.current_thread().name)
        while True:
            print(f"procname={procname_get()}")
            time.sleep(0.2)

    thread = threading.Thread(
        name=thread_name,
        target=dummy_target,
        daemon=True,
    )

    thread.start()

    time.sleep(1)

    os.system("ps -A -T | grep 'hello-kitty'")
