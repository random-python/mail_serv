
from mail_serv_test import *
from mail_serv.profiler import *

os.environ['PROFILER_REPORT_DIR'] = f"{THIS_DIR}/tmp/profiler"


def dummy_fun1(index:int) -> None:
    time.sleep(0.010)


def dummy_fun2(index:int) -> None:
    time.sleep(0.020)


def test_system_profiler():
    print()

    profiler = SystemProfiler()  # active in main thread

    def dummy_thread():
        profiler.interrupt_activate()  # active in extra thread
        for index in range(10):
            dummy_fun1(index)
            dummy_fun2(index)

    for index in range(3):
        thread = threading.Thread(target=dummy_thread)
        thread.daemon = True
        thread.start()
        update_stat_tree(profiler.frame_stat_map)
        output = render_stat_tree(profiler.frame_stat_map)
        print(f"===")
        print(output)
        time.sleep(1)

    for node_guid, node_stat in profiler.frame_stat_map.items():
        print(f"===")
        print(f"node_guid={node_guid}")
        print(f"node_stat={node_stat}")


def test_profiler_session():
    print()

    session = 'tester-session'

    with profiler_session(session):
        for index in range(10):
            dummy_fun1(index)
            dummy_fun2(index)

    report_file = profiler_report_file(session)
    with open(report_file, 'r') as report_text:
        print(report_text.read())


def xxx_test_profiler_thread():
    print()

    session = 'tester-thread'
    profiler = Profiler(interval=profiler_interval())

    def dummy_thread():
        profiler.start()
        for index in range(10):
            dummy_fun1(index)
            dummy_fun2(index)
        profiler.stop()

    for index in range(5):
        thread = threading.Thread(target=dummy_thread)
        thread.daemon = True
        thread.start()
        thread.join()

    profiler_produce_report(profiler, session)

    report_file = profiler_report_file(session)
    with open(report_file, 'r') as report_text:
        print(report_text.read())
