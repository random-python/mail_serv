"""
Control process/thread name
"""

import logging
import ctypes
from ctypes.util import find_library

PR_SET_NAME = 15
PR_GET_NAME = 16

PR_NAME_SIZE = 16

logger = logging.getLogger(__name__)


def library_libc():
    return ctypes.CDLL(find_library('c'))


def procname_set(name:str) -> None:
    "replace process/thread name"
    try:
        name = name[:PR_NAME_SIZE - 1]  # trim to limit
        library_libc().prctl(PR_SET_NAME, name.encode(), 0, 0, 0)
    except Exception as error:
        logger.warn(f"failure: {error}")


def procname_get() -> str:
    "obtain process/thread name"
    try:
        name = ctypes.create_string_buffer(PR_NAME_SIZE)
        library_libc().prctl(PR_GET_NAME, name, 0, 0, 0)
        return name.value.decode()
    except Exception as error:
        logger.warn(f"failure: {error}")
