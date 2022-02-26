
from mail_serv.arkon import *


def test_arkon_regex():
    print()

    assert postfix_regex_maps.match("hello-kitty.maps")
    assert not postfix_regex_maps.match("hello-kitty-maps")

    assert postfix_regex_main.match("main.1.conf")
    assert postfix_regex_main.match("main.2.conf")
    assert not postfix_regex_main.match("main-1.conf")
    assert not postfix_regex_main.match("main-2.conf")

    assert postfix_regex_master.match("master.1.conf")
    assert postfix_regex_master.match("master.2.conf")
    assert not postfix_regex_master.match("master-1.conf")
    assert not postfix_regex_master.match("master-2.conf")


def test_arkon_service():
    print()

#     arkon_service()
#     arkon_tinc()

