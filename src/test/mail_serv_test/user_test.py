
from mail_serv.user import *


def test_user_path():
    print()
    assert user_path('archon@private.dom') == 'private.dom/archon'
