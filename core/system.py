from __future__ import annotations

from platform import node as _node
from platform import release as _release
from platform import system as _system
from time import time as _time

from msgspec import Struct
from psutil import (
    AccessDenied,
    NoSuchProcess,
    boot_time,
    cpu_count,
    cpu_freq,
    cpu_percent,
    disk_partitions,
    disk_usage,
    net_connections,
    net_if_stats,
    net_io_counters,
    process_iter,
    sensors_battery,
    sensors_temperatures,
    swap_memory,
    users,
    virtual_memory,
)

_SKIP_FSTYPES = frozenset(
    (
        "squashfs",
        "tmpfs",
        "devtmpfs",
        "overlay",
        "proc",
        "sysfs",
        "cgroup",
        "cgroup2",
        "debugfs",
        "tracefs",
        "securityfs",
        "fusectl",
        "configfs",
        "pstore",
        "efivarfs",
        "bpf",
        "mqueue",
        "hugetlbfs",
        "rpc_pipefs",
        "binfmt_misc",
    )
)


class resourcestats(Struct, frozen=True):
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float


class cpustats(Struct, frozen=True):
    total_percent: float
    per_core: tuple[float, ...]
    freq_current: float
    freq_min: float
    freq_max: float


class memstats(Struct, frozen=True):
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_available_gb: float
    swap_percent: float
    swap_used_gb: float
    swap_total_gb: float


class diskinfo(Struct, frozen=True):
    device: str
    mountpoint: str
    fstype: str
    percent: float
    used_gb: float
    total_gb: float


class netifinfo(Struct, frozen=True):
    name: str
    sent_mb: float
    recv_mb: float
    is_up: bool
    speed: int


class processinfo(Struct, frozen=True):
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float
    status: str


class sysinfo(Struct, frozen=True):
    system: str
    release: str
    hostname: str
    uptime_seconds: float
    users: tuple[str, ...]
    cpu_logical: int
    cpu_physical: int


class sensorinfo(Struct, frozen=True):
    label: str
    current: float
    high: float
    critical: float


class batteryinfo(Struct, frozen=True):
    percent: float
    power_plugged: bool
    secs_left: int


class resourcemonitor:
    __slots__ = ("interval", "_boot_time")

    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self._boot_time = boot_time()

    def cpu(self) -> cpustats:
        total = cpu_percent(interval=None)
        per_core = tuple(round(x, 1) for x in cpu_percent(interval=None, percpu=True))
        try:
            freq = cpu_freq()
            return cpustats(
                total_percent=round(total, 1),
                per_core=per_core,
                freq_current=round(freq.current, 0),
                freq_min=round(freq.min, 0),
                freq_max=round(freq.max, 0),
            )
        except Exception:
            return cpustats(
                total_percent=round(total, 1),
                per_core=per_core,
                freq_current=0,
                freq_min=0,
                freq_max=0,
            )

    def memory(self) -> memstats:
        mem = virtual_memory()
        swap = swap_memory()
        return memstats(
            ram_percent=round(mem.percent, 1),
            ram_used_gb=round(mem.used / 1e9, 2),
            ram_total_gb=round(mem.total / 1e9, 2),
            ram_available_gb=round(mem.available / 1e9, 2),
            swap_percent=round(swap.percent, 1),
            swap_used_gb=round(swap.used / 1e9, 2),
            swap_total_gb=round(swap.total / 1e9, 2),
        )

    def disks(self) -> tuple[diskinfo, ...]:
        result = []
        for part in disk_partitions():
            if part.fstype in _SKIP_FSTYPES:
                continue
            try:
                usage = disk_usage(part.mountpoint)
                result.append(
                    diskinfo(
                        device=part.device,
                        mountpoint=part.mountpoint,
                        fstype=part.fstype,
                        percent=round(usage.percent, 1),
                        used_gb=round(usage.used / 1e9, 2),
                        total_gb=round(usage.total / 1e9, 2),
                    )
                )
            except (PermissionError, OSError):
                continue
        return tuple(result)

    def network(self) -> tuple[netifinfo, ...]:
        counters = net_io_counters(pernic=True)
        stats = net_if_stats()
        result = []
        for name, stat in counters.items():
            nic_stats = stats.get(name)
            result.append(
                netifinfo(
                    name=name,
                    sent_mb=round(stat.bytes_sent / 1e6, 2),
                    recv_mb=round(stat.bytes_recv / 1e6, 2),
                    is_up=nic_stats.isup if nic_stats else False,
                    speed=nic_stats.speed if nic_stats else 0,
                )
            )
        return tuple(result)

    def connections_count(self) -> int:
        try:
            return len(net_connections())
        except (AccessDenied, PermissionError):
            return -1

    def processes(self, limit: int = 5) -> tuple[processinfo, ...]:
        procs = []
        for proc in process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "status"]
        ):
            try:
                info = proc.info
                procs.append(
                    processinfo(
                        pid=info["pid"],
                        name=info["name"] or "",
                        cpu_percent=round(info["cpu_percent"] or 0, 1),
                        ram_percent=round(info["memory_percent"] or 0, 1),
                        status=info["status"] or "",
                    )
                )
            except (NoSuchProcess, AccessDenied):
                continue
        procs.sort(key=lambda p: p.cpu_percent, reverse=True)
        return tuple(procs[:limit])

    def system(self) -> sysinfo:
        return sysinfo(
            system=_system(),
            release=_release(),
            hostname=_node(),
            uptime_seconds=round(_time() - self._boot_time, 0),
            users=tuple(dict.fromkeys(u.name for u in users())),
            cpu_logical=cpu_count(),
            cpu_physical=cpu_count(logical=False) or 0,
        )

    def temperatures(self) -> tuple[tuple[str, tuple[sensorinfo, ...]], ...]:
        try:
            temps = sensors_temperatures()
        except AttributeError:
            return ()
        if not temps:
            return ()
        result = []
        for name, entries in temps.items():
            sensors = tuple(
                sensorinfo(
                    label=e.label or name,
                    current=round(e.current or 0, 1),
                    high=round(e.high or 0, 1),
                    critical=round(e.critical or 0, 1),
                )
                for e in entries
            )
            result.append((name, sensors))
        return tuple(result)

    def battery(self) -> batteryinfo | None:
        try:
            bat = sensors_battery()
            if bat is None:
                return None
            return batteryinfo(
                percent=round(bat.percent, 1),
                power_plugged=bat.power_plugged,
                secs_left=bat.secs_left,
            )
        except AttributeError:
            return None
