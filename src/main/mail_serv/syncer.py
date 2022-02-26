"""
Syncer plugin service:
* receive events from plugin
* build and apply user sieve filters
* dispatch mailbox replication actions

https://github.com/random-archer/dovecot_plugin_syncer
"""

import os
import re
import time
import queue
import logging
import threading
import functools
from typing import Callable, List
from collections import defaultdict

from mail_serv.config import config_syncer_pipe
from mail_serv.sieve import sieve_build_user, sieve_invoke_user
from mail_serv.tinker import tinker_node_iterate
from mail_serv.replicate import replicate_with_guid
from mail_serv.support import parse_conf_text, count_dict_list
from mail_serv.support import fs_mkdir, fs_rmany, fs_chmod, fs_chown
from mail_serv.profiler import profiler_interval, profiler_enable, profiler_report_file
from mail_serv.profiler import SystemProfiler, update_stat_tree, render_stat_tree
from mail_serv.procname import procname_set

logger = logging.getLogger(__name__)

# event batch collector
# TODO disk based queue
syncer_event_queue = queue.Queue()

# continous multi-threaded sampling profiler
syncer_system_profiler = SystemProfiler(interval=profiler_interval())


def syncer_service():
    "service entry"
    logger.info(f"startup")
    syncer_setup_consumer()
    syncer_setup_profiler()
    pipe_path = config_syncer_pipe()
    event_reactor = syncer_event_reactor
    syncer_make_pipe(pipe_path)
    syncer_event_producer(pipe_path, event_reactor)  # main thread


def syncer_setup_consumer() -> None:
    "ensure event consumer thread"
    threading.Thread(
        name='syncer-consumer',
        daemon=True,
        target=syncer_event_consumer,
    ).start()


def syncer_setup_profiler() -> None:
    "ensure profiler reporter thread"
    if not profiler_enable():
        return
    threading.Thread(
        name='syncer-profiler',
        daemon=True,
        target=syncer_profiler_reporter,
    ).start()


def syncer_profiler_reporter() -> None:
    "profiler stats reporter thread"

    procname_set(threading.current_thread().name)

    if profiler_enable():
        syncer_system_profiler.interrupt_activate()

    profiler_period = float(os.environ.get('SYNCER_PROFILER_PERIOD', 15))  # seconds
    while True:
        try:
            time.sleep(profiler_period)
            syncer_report_stats()
        except Exception as error:
            logger.warn(f"failure: {error}")
            time.sleep(1)  # prevent error spin


def syncer_report_stats() -> None:
    "produce service profiler report"
    session = 'syncer-service'
    report_file = profiler_report_file(session)
    frame_stat_map = syncer_system_profiler.frame_stat_map
    update_stat_tree(frame_stat_map)
    render_text = render_stat_tree(frame_stat_map)
    with open(report_file, "w") as report_text:
        report_text.write(render_text)


def syncer_make_pipe(
        pipe_path:str,
        own_uid="service",
        own_gid="dovecot",
    ) -> None:
    "produce fifo pipe for the syncer plugin"
    pipe_dir = os.path.dirname(pipe_path)
    fs_mkdir(pipe_dir)
    fs_rmany(pipe_path)
    os.mkfifo(pipe_path)
    fs_chmod(pipe_dir, mode=0o660, dir_on=0o2770)
    fs_chown(pipe_dir, own_uid, own_gid)


def syncer_event_producer(
        pipe_path:str,
        event_reactor:Callable=lambda line : logger.debug(line),
    ):
    "syncer pipe event reader thread"
    logger.debug(f"setup: pipe_path={pipe_path}")
    while True:  # perform forever
        try:
            with open(pipe_path, "r") as line_read:
                for line in line_read:
                    try:
                        event_reactor(line)
                    except Exception as error:
                        logger.warn(f"pipe react failure: {error}")
        except Exception as error:
            logger.warn(f"pipe open failure: {error}")
            time.sleep(1)  # prevent error spin


def syncer_event_reactor(event:str) -> None:
    "syncer pipe event queue feeder"
    syncer_event_queue.put(event, block=False)  # should never fail


def syncer_event_consumer() -> None:  # TODO thread pool
    "syncer event queue consumer thread"

    procname_set(threading.current_thread().name)

    if profiler_enable():
        syncer_system_profiler.interrupt_activate()

    timer_limit = int(os.environ.get('SYNCER_TIMER_LIMIT', 3))  # number
    timer_delay = float(os.environ.get('SYNCER_TIMER_DELAY', 1.0))  # seconds
    logger.debug(f"setup: timer_limit={timer_limit} timer_delay={timer_delay}")

    queue_size_max = 0  # measured value

    def measure_queue_size():
        nonlocal queue_size_max
        queue_size = syncer_event_queue.qsize()
        if queue_size > queue_size_max:
            queue_size_max = queue_size
            logger.warn(f"queue_size_max={queue_size_max}")

    while True:  # perform forever
        try:
            timer_count = 0  # count empty get
            event_list = list()  # collect event batch
            while True:  # drain queue within a timeout
                try:
                    measure_queue_size()
                    event = syncer_event_queue.get(block=False)  # fails on empty
                    event_list.append(event)  # collect event batch
                    timer_count = 0  # reset timer on proper get
                except queue.Empty:  # trap empty queue condition
                    time.sleep(timer_delay)  # wait after emtpy condition
                    if event_list:  # count only with events
                        timer_count += 1  # count empty get
                    if timer_count >= timer_limit:  # timer wait limit
                        break  # ready to consume event batch
            syncer_process_events(event_list)  # consume event batch
        except Exception as error:
            logger.warn(f"failure: {error}")
            time.sleep(1)  # prevent error spin


@functools.lru_cache(maxsize=1)
def syncer_regex_change() -> re.Pattern:
    "regex pattern in chng_type to trigger filter build"
    "by default react to mailbox create/delete/rename operations"
    regex = os.environ.get('SYNCER_REGEX_CHANGE', '^mailbox_(create|delete|rename)$')
    return re.compile(regex)


@functools.lru_cache(maxsize=1)
def syncer_regex_define() -> re.Pattern:
    "regex pattern in mbox_name to trigger filter build"
    "by default expect define in the form of name@domain"
    regex = os.environ.get('SYNCER_REGEX_DEFINE', '^(.+)([^/]+)@([^/]+)$')
    return re.compile(regex, re.RegexFlag.IGNORECASE)


@functools.lru_cache(maxsize=1)
def syncer_regex_invoke() -> re.Pattern:
    "regex pattern in mbox_name to trigger filter apply"
    "by default react only to inbox events"
    regex = os.environ.get('SYNCER_REGEX_INVOKE', '^(inbox)$')
    return re.compile(regex, re.RegexFlag.IGNORECASE)


@functools.lru_cache(maxsize=1)
def syncer_regex_replicate() -> re.Pattern:
    "regex pattern in mbox_name to trigger mailbox replication"
    "by default replicate all user mailboxes"
    regex = os.environ.get('SYNCER_REGEX_REPLICATE', '^(.+)$')
    return re.compile(regex, re.RegexFlag.IGNORECASE)


def syncer_process_events(event_list: List[str]) -> None:
    """
    process collected event batch:
    * build filters
    * apply filters
    * replicate mailboxes
    """

    sieve_build_set = set()  # set of user_name
    sieve_invoke_map = defaultdict(set)  # map: user_name -> set of mbox_name
    replicate_task_map = defaultdict(set)  # map: user_name -> set of mbox_guid

    regex_change = syncer_regex_change()
    regex_define = syncer_regex_define()
    regex_invoke = syncer_regex_invoke()
    regex_replicate = syncer_regex_replicate()

    # formulate requests
    for event in event_list:
        conf_dict = parse_conf_text(event, separator='\t')
        chng_type = conf_dict['chng_type']
        user_name = conf_dict['user_name']
        mbox_name = conf_dict['mbox_name']
        mbox_guid = conf_dict['mbox_guid']
        # collect sieve biuld request
        if regex_change.match(chng_type) and regex_define.match(mbox_name):
            sieve_build_set.add(user_name)
        # collect sieve apply request
        if regex_invoke.match(mbox_name):
            sieve_invoke_map[user_name].add(mbox_name)
        # collect mailbox replicate request
        if regex_replicate.match(mbox_name):
            replicate_task_map[user_name].add(mbox_guid)

    logger.debug(
        f"request: "
        f"event_list={len(event_list)} "
        f"filter_build={len(sieve_build_set)} "
        f"filter_invoke={count_dict_list(sieve_invoke_map)} "
        f"replicate_task={count_dict_list(replicate_task_map)} "
    )

    # build sieve filter
    for user_name in sieve_build_set:
        try:
            sieve_build_user(user_name)
        except Exception as error:
            logger.warn(f"sieve build failure: {user_name} :: {error}")

    # invoke sieve filter
    for user_name, mbox_list in sieve_invoke_map.items():
        for mbox_name in mbox_list:
            try:
                sieve_invoke_user(user_name, mbox_name)
            except Exception as error:
                logger.warn(f"sieve invoke failure: {user_name} :: {error}")

    # replicate user mailbox
    for user_name, guid_list in replicate_task_map.items():
        for mbox_guid in guid_list:

            def syncer_replicate(node_addr, node_port):
                func_info = f"{user_name}/{mbox_guid} {node_addr}:{node_port}"
                try:
                    logger.debug(func_info)
                    replicate_with_guid(user_name, mbox_guid, node_addr, node_port)
                except Exception as error:
                    logger.warn(f"failure: {func_info} :: {error}")

            tinker_node_iterate(syncer_replicate)
