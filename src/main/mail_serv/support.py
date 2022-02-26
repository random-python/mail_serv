"""
Support functions
"""

import os
import stat
import time
import shutil
import logging
import functools
from contextlib import contextmanager
from typing import Mapping, List, Callable, Any

logger = logging.getLogger(__name__)


def parse_conf_list(line_list:List[str]) -> Mapping[str, str]:
    "extract key=value from list as dict"
    conf_dict = dict()
    for line in line_list:
        if '=' in line:
            key, value = line.partition("=")[::2]
            key = key.lower().strip()  # cased to lower
            value = value.strip()  # keep case
            conf_dict[key] = value
    return conf_dict


def parse_conf_text(conf_text:str, separator:str='\n') -> Mapping[str, str]:
    "extract key=value from text as dict"
    line_list = conf_text.split(separator)
    return parse_conf_list(line_list)


def parse_conf_file(conf_file:str) -> Mapping[str, str]:
    "extract key=value from file.conf as dict"
    with open(conf_file, "r") as line_list:
        return parse_conf_list(line_list)


def convert_text2bool(value:str) -> bool:
    "convert text representation of boolean"
    if value:
        return str(value).lower() in ('true', 'yes', 'on', 't', '1')
    else:
        return False


def count_dict_list(data:dict) -> int:
    "produce linear sum of mapping"
    return sum([len(entry) for entry in data.values()])


def fs_concat(target:str, source_list:List[str]) -> None:
    "concatenate multiple source files into single target file"
    with open(target, 'wb') as target_file:
        for source in source_list:
            with open(source, 'rb') as source_file:
                shutil.copyfileobj(source_file, target_file)


def fs_mkdir(path:str) -> None:
    "make nested directory tree"
    if os.path.isdir(path):
        pass
    else:
        os.makedirs(path, exist_ok=True)


def fs_rmany(path:str) -> None:
    "remove file or tree"
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def fs_strip_eol(line:str) -> str:
    "remove head/tail end of line characters from a line"
    return line.strip('\r\n')


def fs_visit(root_path:str, dir_action:Callable, file_action:Callable) -> None:
    "apply action to file system tree"
    dir_action(root_path)
    for base_path, dir_name_list, file_name_list in os.walk(root_path):
        for dir_name in dir_name_list:
            dir_path = os.path.join(base_path, dir_name)
            try:
                dir_action(dir_path)
            except Exception as error:
                action = dir_action.__name__
                logger.warn(f"failure: {action}: {error}")
        for file_name in file_name_list:
            file_path = os.path.join(base_path, file_name)
            try:
                file_action(file_path)
            except Exception as error:
                action = file_action.__name__
                logger.warn(f"failure: {action}: {error}")


def fs_chown(root_path:str, user:Any, group:Any) -> None:
    "change tree ownership recursively"
    if isinstance(user, str):
        uid = shutil._get_uid(user)
        assert uid is not None, f"no user: {user}"
    else:
        uid = user
    if isinstance(group, str):
        gid = shutil._get_gid(group)
        assert gid is not None, f"no group: {group}"
    else:
        gid = group

    def chown(path:str) -> None:
        os.chown(path, uid, gid)

    fs_visit(root_path, chown, chown)


def fs_chmod(root_path:str,
        mode:int=None,
        dir_on:int=None, dir_off:int=None,
        file_on:int=None, file_off:int=None,
    ) -> None:
    "change tree permissions recursively"

    def chmod(path:str, on:int, off:int,) -> None:
        past_mode = stat.S_IMODE(os.lstat(path).st_mode)
        next_mode = past_mode
        if mode:
            next_mode = mode
        if on:
            next_mode = next_mode | on
        if off:
            next_mode = next_mode & ~off
        if past_mode == next_mode:
            pass
        else:
            os.chmod(path, next_mode)

    def dir_chmod(path):
        chmod(path, dir_on, dir_off)

    def file_chmod(path):
        chmod(path, file_on, file_off)

    fs_visit(root_path, dir_chmod, file_chmod)


def fs_copy(src:str, dst:str, check_ignore:Callable=None) -> None:
    "copy file system tree recursively"
    if os.path.isdir(src):
        if not os.path.isdir(dst):
            os.makedirs(dst, exist_ok=True)
        path_name_list = os.listdir(src)
        if check_ignore is not None:
            ignore_set = check_ignore(src, path_name_list)
        else:
            ignore_set = set()
        for path_name in path_name_list:
            if path_name not in ignore_set:
                src_path = os.path.join(src, path_name)
                dst_path = os.path.join(dst, path_name)
                fs_copy(src_path, dst_path, check_ignore)
    else:
        shutil.copyfile(src, dst)
        shutil.copystat(src, dst)


def fs_size(root_path:str) -> int:
    "measure directory disk space"
    path_size = 0

    def dir_size(path:str) -> None:
        pass

    def file_size(path:str) -> None:
        nonlocal path_size
        if os.path.islink(path):
            pass
        else:
            path_size += os.path.getsize(path)

    fs_visit(root_path, dir_size, file_size)

    return path_size


def fs_mask() -> int:
    "extract current umask"
    mask = os.umask(0)
    os.umask(mask)
    return mask


def report_time(func:Callable) -> Any:
    "report function execution time"

    @functools.wraps(func)
    def with_time(*args, **kwargs):
        time_start = time.time()
        result = func(*args, **kwargs)
        time_finish = time.time()
        time_diff = int(time_finish - time_start)
        func_name = func.__name__
        logger.debug(f"{func_name} @ {time_diff} sec")
        return result

    return with_time


@contextmanager
def filesys_session(
        process_umask:int=0o0007,  # u=rwx,g=rwx,o=
    ):
    "invoke function with specific file mask"
    process_umask = os.umask(process_umask)
    try:
        yield
    finally:
        os.umask(process_umask)
