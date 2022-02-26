
from mail_serv.sieve import *


def test_sieve_regex():
    print()

    entry_list = [
        "Vendor",
        "Vendor/Company",
        "Vendor/Company/First Last",
        "Vendor/Company/First Last first.last@company.com",
        "Vendor/Company/First Last [keyword] first.last@company.com",
    ]

    for entry in entry_list:
        match_root = sieve_regex_base.match(entry)
        match_define = sieve_regex_define.match(entry)
        print(f"entry={entry} match_root={match_root} match_define={match_define}")


def test_sieve_regex_define_1():
    print()
    entry = "Vendor/Company/First Last first.last@company.com"
    match_define = sieve_regex_define.match(entry)
    assert match_define.group(1) == "Vendor"
    assert match_define.group(2) == None
    assert match_define.group(3) == "first.last@company.com"


def test_sieve_regex_define_2():
    print()
    entry = "Vendor/Company/First Last [keyword] first.last@company.com"
    match_define = sieve_regex_define.match(entry)
    assert match_define.group(1) == "Vendor"
    assert match_define.group(2) == "[keyword]"
    assert match_define.group(3) == "first.last@company.com"

