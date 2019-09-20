"""
TODO
Replicate config files inside tinc mesh
"""

import os
import time
import logging
import threading
import functools
from typing import List

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def filer_base_dir() -> str:
    "root of watch folder"
    return os.environ.get('FILESYNC_BASE_DIR', "/etc/filesync")


@functools.lru_cache(maxsize=1)
def filer_settle_timeout() -> float:
    "event stream quiet timeout"
    return float(os.environ.get('FILESYNC_SETTLE_TIMEOUT', "3.0"))


@functools.lru_cache(maxsize=1)
def filer_regex_include() -> List[str]:
    "sync files matching regular expression"
    regex_include = os.environ.get('FILESYNC_REGEX_INCLUDE', ".*")
    return regex_include.split(' ')


@functools.lru_cache(maxsize=1)
def filer_regex_exclude() -> List[str]:
    "sync files matching regular expression"
    regex_exclude = os.environ.get('FILESYNC_REGEX_EXCLUDE', "")
    return regex_exclude.split(' ')


def filer_monitor_task() -> None:
    "inotify event thread"
    while True:
        try:
            pass
        except Exception as error:
            logger.warning(f"failure: {error}")
            time.sleep(1)  # prevent error spin


def filer_produce_monitor() -> None:
    ""
    "ensure inotify thread"
    threading.Thread(
        name='filesync-task',
        daemon=True,
        target=filer_monitor_task,
    ).start()
