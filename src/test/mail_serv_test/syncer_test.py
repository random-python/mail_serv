
import time

from mail_serv.syncer import *

USER = os.environ['USER']

def test_syncer_make_pipe():
    print()
    pipe_path = "/tmp/syncer-make/pipe"
    syncer_make_pipe(pipe_path, USER, USER)


def test_syncer_read_pipe():
    print()
    pipe_path = "/tmp/syncer-read/pipe"
    syncer_make_pipe(pipe_path, USER, USER)
    reader_thread = threading.Thread(target=syncer_event_producer, args=[pipe_path])
    reader_thread.setDaemon(True)
    reader_thread.start()
    with open(pipe_path, "w") as line_send:
        for index in range(7):
            print(f"send={index}")
            line_send.write(f"read={index}\n")
            line_send.flush()
            time.sleep(0.1)


def test_syncer_event_process():
    print()

    syncer_event = "chng_type=mailbox_create\tuser_name=supre-user\tmbox_name=inbox\tmbox_guid=1234"

    syncer_setup_consumer()


def test_syncer_regex_define():
    print()
    regex = syncer_regex_define()
    assert regex.match('Vendor/Company @company.com')
    assert regex.match('Vendor/Company/Name @company.com')
    assert regex.match('Vendor/Company/First Last first.last@company.com')
    assert regex.match('Vendor/Company/First Last [keyword] first.last@company.com')


def test_syncer_regex_change():
    print()
    regex = syncer_regex_change()
    assert regex.match('mailbox_create')
    assert regex.match('mailbox_delete')
    assert regex.match('mailbox_rename')


def test_syncer_regex_invoke():
    print()
    regex = syncer_regex_invoke()
    assert regex.match('INBOX')
    assert regex.match('inbox')


def test_syncer_regex_replicate():
    print()
    regex = syncer_regex_replicate()
    assert regex.match('INBOX')
    assert regex.match('inbox')
    assert regex.match('Vendor/Company')
    assert regex.match('Vendor/Company @company.com')
    assert regex.match('Vendor/Company/Name @company.com')
    assert regex.match('Vendor/Company/First Last first.last@company.com')
    assert regex.match('Vendor/Company/First Last [keyword] first.last@company.com')
