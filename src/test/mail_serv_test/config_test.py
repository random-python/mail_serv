from mail_serv_test import *
from mail_serv.config import *


def test_config_func():
    print()

    os.environ['DOVECOT_CONFIG'] = f"{THIS_DIR}/etc/dovecot/dovecot.conf"

    assert config_doveadm_password() == 'abrakadabra'
    assert config_client_ca_file() == '/hello/client'
    assert config_doveadm_port() == '1234'
    assert config_mail_home('person@domain') == '/home/data/domain/person'
    assert config_mail_location('person@domain') == '/home/data/domain/person/mail'
    assert config_sieve_path('person@domain') == '/home/data/domain/person/sieve'
    assert config_sieve_active('person@domain') == '/home/data/domain/person/active.sieve'
    assert config_sieve_default('person@domain') == '/home/data/domain/person/active.sieve'
    assert config_syncer_dir('person@domain') == '/home/data/domain/person/syncer'
    assert config_syncer_pipe() == '/run/dovecot/syncer/pipe'

    mail_layout = config_mail_layout('person@domain')
    assert mail_layout['TYPE'] == 'maildir'
    assert mail_layout['PATH'] == '~/mail'
    assert mail_layout['LAYOUT'] == 'fs'
    assert mail_layout['DIRNAME'] == '_m_a_i_l_'
    assert mail_layout['UTF-8'] == 'true'
