
import sys
import time

from mail_serv_test import THIS_DIR
from mail_serv.support import *

USER = os.environ['USER']


def test_count_dict_list():
    print()

    data = dict([
        ('a', [1, 2, 3]),
        ('b', ['1', '2', '3']),
        ('c', set(['a', 'b', 'c'])),
    ])

    assert count_dict_list(data) == 9


def test_strip_line():
    print()

    assert fs_strip_eol('\n\r\n\rline\n\r\n\r') == 'line'


def test_fs_chown():
    print()
    test_dir = f"{THIS_DIR}/tmp"
    uid = USER
    gid = USER
    fs_chown(test_dir, uid, gid)


def test_fs_chmod():
    print()
    test_dir = f"{THIS_DIR}/tmp"
    dir_on = 0o755
    dir_off = 0o007
    file_on = 0o676
    file_off = 0o027
    fs_chmod(test_dir,
        dir_on=dir_on, dir_off=dir_off,
        file_on=file_on, file_off=file_off,
    )
    os.system(f"ls -lasR {test_dir}")


def test_fs_copy():
    print()
    src_dir = f"{THIS_DIR}/tmp"
    dst_dir = f"{THIS_DIR}/tmp-1"
    fs_copy(src_dir, dst_dir)
    fs_copy(src_dir, dst_dir)


def test_get_pwd():
    print()
    root_uid = shutil._get_uid('root')
    print(f"root_uid: {root_uid}")
    root_gid = shutil._get_gid('root')
    print(f"root_gid: {root_gid}")


def test_fs_size():
    print()
    test_dir = f"{THIS_DIR}/tmp"
    path_size = fs_size(test_dir)
    print(f"path_size={path_size:,}")


def test_report_time():
    print()

    @report_time
    def some_work():
        time.sleep(0.1)

    some_work()


def test_service_session():
    print()
    print(f"umask={oct(fs_mask())}")
    with filesys_session():
        print(f"umask={oct(fs_mask())}")
    print(f"umask={oct(fs_mask())}")
