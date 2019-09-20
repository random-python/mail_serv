"""
Logging system setup
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from mail_serv.support import fs_mkdir


def logging_level() -> str:
    return os.environ.get('LOGGING_LEVEL', 'debug').upper().strip()


def logging_format_date() -> str:
    return os.environ.get('LOGGING_FORMAT_DATE', '%Y-%m-%d %H:%M:%S').strip()


def logging_format_record() -> str:
    return os.environ.get('LOGGING_FORMAT_ENTRY', (
        "%(asctime)s %(levelname)-.4s "
        "%(module)s:%(lineno)03d/%(funcName)s  "
        "%(message)s "
    )).strip()


def logging_file_dir() -> str:
    return os.environ.get('LOGGING_FILE_DIR', '/var/lib/mail_serv/logger').strip()


def logging_file_level() -> str:
    return os.environ.get('LOGGING_FILE_LEVEL', 'info').upper().strip()


def logging_file_chunk() -> int:
    return int(os.environ.get('LOGGING_FILE_CHUNK', '100000').strip())


def logging_file_count() -> int:
    return int(os.environ.get('LOGGING_FILE_COUNT', '3').strip())


def logging_setup():

    logger_dir = logging_file_dir()
    logger_file = f"{logger_dir}/default.log"

    fs_mkdir(logger_dir)

    logging.basicConfig(
        level=logging_level(),
        datefmt=logging_format_date(),
        format=logging_format_record(),
    )

    formatter = logging.Formatter(
        datefmt=logging_format_date(),
        fmt=logging_format_record(),
    )

    handler = RotatingFileHandler(
        filename=logger_file,
        maxBytes=logging_file_chunk(),
        backupCount=logging_file_count(),
    )

    handler.setLevel(logging_file_level())
    handler.setFormatter(formatter)

    logging.getLogger().addHandler(handler)
