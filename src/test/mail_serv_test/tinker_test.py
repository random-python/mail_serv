
from mail_serv_test import *
from mail_serv.tinker import *


def test_tinker_default():
    print()
    assert tinker_etc_dir() == '/etc/tinc'
    assert tinker_mail_dir() == '/etc/tinc/mail'
    assert tinker_host_dir() == '/etc/tinc/mail/hosts'
    assert tinker_node_dir() == '/etc/tinc/mail/nodes'
    assert tinker_conf_file() == '/etc/tinc/mail/tinc.conf'


def test_tinker_config():
    print()
    os.environ['TINKER_ETC_DIR'] = f"{THIS_DIR}/etc/tinc"
    print(tinker_conf_dict())
    assert tinker_host_name() == 'serv_1'
    print(tinker_node_list())
    assert tinker_node_list() == ['serv_2', 'serv_3']

    def node_func(node_addr, node_port):
        print(f"node_addr={node_addr} node_port={node_port}")

    tinker_node_iterate(node_func)


def test_tinker_script_addr():
    print()
    os.environ['SUBNET'] = "192.168.1.123/24"
    assert tinker_script_addr() == '192.168.1.123'


def test_tinker_skip_list():
    print()
    assert tinker_skip_list() == ['readme.md', 'readme.txt', 'readme.rst']
