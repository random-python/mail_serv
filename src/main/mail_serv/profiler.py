"""
Code sampling profiler
"""

import os
import sys
import time
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Mapping, List, Set, Iterable
from time import process_time
from contextlib import contextmanager

from pyinstrument import Profiler
from pyinstrument.session import Session
from pyinstrument.renderers.console import ConsoleRenderer
from pyinstrument.low_level.stat_profile import setstatprofile

from mail_serv.support import convert_text2bool, fs_mkdir

logger = logging.getLogger(__name__)


def profiler_enable() -> bool:
    "enable profiler sessions, yes by default"
    return convert_text2bool(os.environ.get('PROFILER_ENABLE', 'true'))


def profiler_interval() -> float:
    "define profiler sampling interval in seconds"
    return float(os.environ.get('PROFILER_INTERVAL', '0.001'))


def profiler_report_dir() -> str:
    "define profiler output directory"
    return os.environ.get('PROFILER_REPORT_DIR', '/var/lib/mail_serv/profiler')


def profiler_report_file(session:str) -> str:
    "define profiler output report file"
    report_dir = profiler_report_dir()
    return f"{report_dir}/{session}.txt"


def profiler_produce_report(profiler:Profiler, session:str) -> None:
    "persist profiler session report"
    report_dir = profiler_report_dir()
    report_file = profiler_report_file(session)
    fs_mkdir(report_dir)
    with open(report_file, "w") as report_text:
        report_text.write(profiler.output_text())


@contextmanager
def profiler_session(session:str) -> None:
    "invoke code with sampling profiler"
    has_profiler = profiler_enable()
    if has_profiler:
        profiler = Profiler(interval=profiler_interval())
        profiler.start()
    try:
        yield
    finally:
        if has_profiler:
            profiler.stop()
            profiler_produce_report(profiler, session)


def profiler_extract_session(profiler:Profiler) -> Session:
    "extract session from running profiler"
    session = Session(
        frame_records=profiler.frame_records,
        start_time=profiler._start_time,
        duration=time.time() - profiler._start_time,
        sample_count=len(profiler.frame_records),
        start_call_stack=profiler._start_call_stack,
        cpu_time=process_time() - profiler._start_process_time,
        program=' '.join(sys.argv),
    )
    return session


def profiler_render_session(session:Session) -> str:
    return ConsoleRenderer().render(session)

#
#
#


@dataclass
class FrameStat:
    "frame statistics collector"

    count:int = 0  # running invocation count, realtime
    time_this:float = 0  # time spent in this frame, realtime
    time_total:float = -1  # time spent in this and below, calculated
    frame:object = None  # frame reported by interrupt, realtime, can be updated
    leaf_guid_set:Set[str] = field(default_factory=set)  # dependencies, calculated

    @property
    def guid(self) -> str:
        return  frame_node_guid(self.frame)

    @property
    def file_path(self) -> str:  # absolute module path
        return self.frame.f_code.co_filename

    @property
    def file_name(self) -> str:  # module.py name only
        return os.path.basename(self.file_path)

    @property
    def unit_name(self) -> str:  # "package/module.py"
        base_name = os.path.basename(os.path.dirname(self.file_path))
        return f"{base_name}/{self.file_name}"

    @property
    def line_num(self) -> int:  # start of function
        return self.frame.f_code.co_firstlineno

    @property
    def code_name(self) -> str:  # module/function
        return self.frame.f_code.co_name

    @property
    def unit_time(self) -> str:  # time per call
        if self.count:
            time = self.time_this / self.count
        else:
            time = 0.0
        return "{:.3f}".format(time)

    @property
    def total_time(self) -> str:
        return "{:.3f}".format(self.time_total)

    def render_line(self, line_tabs:str) -> str:
        return (
            f"{line_tabs}{self.total_time} [{self.unit_time}] "
            f"{self.code_name} @ "
            f"{self.unit_name}:{self.line_num} "
        )


class SystemProfiler():
    "continous multi-threaded sampling profiler"

    interval:float
    time_init:float
    time_past:float
    profiler_lock:threading.Lock
    frame_stat_map:Mapping[str, FrameStat]

    def __init__(self, interval:float=0.001):
        self.interval = interval
        self.frame_stat_map = dict()
        self.time_init = time.perf_counter()
        self.time_past = time.perf_counter()
        self.profiler_lock = threading.Lock()

    def interrupt_activate(self) -> None:
        "use to enable profiler for a given thread"
        setstatprofile(self.profiler_interrupt, self.interval)

    def interrupt_deactivate(self) -> None:
        "use to disable profiler for a given thread"
        setstatprofile(None)

    def profiler_interrupt(self, frame:object, event:str, *_) -> None:
        "react to periodic interrupt from python core"
        with self.profiler_lock:
            time_next = time.perf_counter()
            time_past = self.time_past
            self.time_past = time_next
        time_diff = time_next - time_past
        if event == 'call':
            frame = frame.f_back
        node_guid = frame_node_guid(frame)
        node_stat = self.frame_stat_map.get(node_guid, None)  # thread safe
        if not node_stat:
            self.frame_stat_map[node_guid] = FrameStat()  # last wins
            node_stat = self.frame_stat_map[node_guid]
        node_stat.count += 1  # thread safe
        node_stat.time_this += time_diff  # thread safe
        node_stat.frame = frame  # last wins


def frame_base_guid(frame:object) -> str:
    "extract stack frame parent identity"
    frame = frame.f_back
    return frame_node_guid(frame) if frame else None


def frame_node_guid(frame:object) -> str:
    "produce complex stack frame identity"
    self_guid = frame_self_guid(frame)
    frame = frame.f_back
    base_guid = frame_self_guid(frame) if frame else "---"
    return f"{base_guid}>{self_guid}"


def frame_self_guid(frame:object) -> str:
    "produce simple stack frame identity"
    f_code = frame.f_code
    return f"{f_code.co_filename}:{f_code.co_firstlineno}:{f_code.co_name}"


def update_total_time(node_stat:FrameStat, frame_stat_map:Mapping[str, FrameStat]) -> None:
    "update total time cache values"
    if node_stat.time_total < 0:  # needs update
        node_stat.time_total = node_stat.time_this
        for leaf_guid in node_stat.leaf_guid_set:
            leaf_stat = frame_stat_map.get(leaf_guid, None)
            if leaf_stat:
                update_total_time(leaf_stat, frame_stat_map)
                node_stat.time_total += leaf_stat.time_total


def update_stat_tree(frame_stat_map:Mapping[str, FrameStat]) -> None:
    "produce eventually consistent call tree with total time"

    # ensure missing nodes
    for node_stat in list(frame_stat_map.values()):
        frame = node_stat.frame
        while frame is not None:
            unit_guid = frame_node_guid(frame)
            if not unit_guid in frame_stat_map:
                frame_stat_map[unit_guid] = FrameStat(frame=frame)
            frame = frame.f_back

    # update hierarchy links
    for node_guid, node_stat in list(frame_stat_map.items()):
        node_stat.time_total = -1  # reset time cache
        base_guid = frame_base_guid(node_stat.frame)
        if base_guid:
            base_stat = frame_stat_map.get(base_guid, None)
            if base_stat:
                base_stat.leaf_guid_set.add(node_guid)

    # update total time cache
    for node_stat in list(frame_stat_map.values()):
        update_total_time(node_stat, frame_stat_map)


def frame_root_list(frame_stat_map:Mapping[str, FrameStat]) -> List[str]:
    "discover frame stack thread entry points"
    root_guid_set = set()
    for node_guid, node_stat in list(frame_stat_map.items()):
        base_guid = frame_base_guid(node_stat.frame)
        if not base_guid:
            root_guid_set.add(node_guid)
    root_guid_list = list(root_guid_set)
    root_guid_list.sort()
    return root_guid_list


def render_stat_tree(frame_stat_map:Mapping[str, FrameStat]) -> str:
    "produce compete call tree representation"
    root_guid_list = frame_root_list(frame_stat_map)
    root_text_list = []
    for root_guid in root_guid_list:
        root_text = render_stat_root(root_guid, frame_stat_map)
        root_text_list.append(root_text)
    return "\n".join(root_text_list)


def render_stat_root(
        root_guid:str,
        frame_stat_map:Mapping[str, FrameStat],
    ) -> str:
    "produce call tree for a single thread root"
    line_tabs = ""
    line_list = []
    frame_memo_set = set()  # memorize visited nodes
    render_stat_node(root_guid, line_tabs, line_list, frame_memo_set, frame_stat_map)
    return "\n".join(line_list)


def render_stat_node(
        base_guid:str,
        line_tabs:str ,
        line_list:List[str],
        frame_memo_set:Set[str],
        frame_stat_map:Mapping[str, FrameStat],
    ) -> None:
    "produce linear call tree representation"
    if base_guid in frame_memo_set:
        return  # prevent multiple inheritance and recursion
    else:
        frame_memo_set.add(base_guid)
    base_stat = frame_stat_map[base_guid]
    line_text = base_stat.render_line(line_tabs)
    line_list.append(line_text)
    line_tabs += "  "
    for node_guid in base_stat.leaf_guid_set:
        render_stat_node(node_guid, line_tabs, line_list, frame_memo_set, frame_stat_map)


def remove_stat_deps(
        frame_stat_map:Mapping[str, FrameStat],
    ) -> None:
    "remove frame dependencies before update"
    for node_stat in list(frame_stat_map.values()):
        node_stat.leaf_guid_set.clear()
