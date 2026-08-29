"""当前 SecForge 进程的资源占用采样。"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessResourceUsage:
    """单次进程资源占用采样结果。"""

    cpu_percent: float
    memory_bytes: int
    memory_percent: float


class ProcessResourceMonitor:
    """基于标准库采样当前进程，避免为标题栏引入额外依赖。"""

    def __init__(self) -> None:
        self._last_cpu_time = time.process_time()
        self._last_sample_time = time.perf_counter()

    def sample(self) -> ProcessResourceUsage:
        """返回自上次采样以来的 CPU 占用和当前内存工作集。"""

        current_cpu_time = time.process_time()
        current_sample_time = time.perf_counter()
        elapsed = current_sample_time - self._last_sample_time
        cpu_percent = 0.0 if elapsed <= 0 else (current_cpu_time - self._last_cpu_time) / elapsed * 100
        self._last_cpu_time = current_cpu_time
        self._last_sample_time = current_sample_time

        memory_bytes = _current_process_memory_bytes()
        total_memory_bytes = _total_physical_memory_bytes()
        memory_percent = 0.0 if total_memory_bytes <= 0 else memory_bytes / total_memory_bytes * 100
        return ProcessResourceUsage(cpu_percent, memory_bytes, memory_percent)


def _current_process_memory_bytes() -> int:
    """读取当前进程的常驻内存；Windows 下使用工作集大小。"""

    if sys.platform == "win32":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
        get_process_memory_info.restype = wintypes.BOOL
        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = wintypes.HANDLE
        success = get_process_memory_info(get_current_process(), ctypes.byref(counters), counters.cb)
        return int(counters.WorkingSetSize) if success else 0

    if sys.platform.startswith("linux"):
        try:
            resident_pages = int(Path("/proc/self/statm").read_text().split()[1])
            return resident_pages * os.sysconf("SC_PAGE_SIZE")
        except (IndexError, OSError, ValueError):
            return 0
    return 0


def _total_physical_memory_bytes() -> int:
    """读取物理内存总量，以便展示当前进程的内存占比。"""

    if sys.platform == "win32":
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        global_memory_status_ex = ctypes.windll.kernel32.GlobalMemoryStatusEx
        global_memory_status_ex.argtypes = [ctypes.POINTER(MemoryStatusEx)]
        global_memory_status_ex.restype = wintypes.BOOL
        return int(status.ullTotalPhys) if global_memory_status_ex(ctypes.byref(status)) else 0

    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return 0
