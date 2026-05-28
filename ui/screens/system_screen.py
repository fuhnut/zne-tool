from __future__ import annotations

import asyncio
import time
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Label

from core.system import resourcemonitor

_COLOURS = (
    "#ff1111",
    "#ff2244",
    "#ff1166",
    "#ff0088",
    "#dd2299",
    "#bb33aa",
    "#9922bb",
    "#8822cc",
    "#7722dd",
    "#6622ee",
    "#5522ff",
    "#4422ff",
    "#3322ff",
    "#4422ff",
    "#5522ff",
    "#6622ff",
    "#7722ff",
    "#8822ee",
    "#9922dd",
    "#bb22cc",
    "#dd22aa",
    "#ff1199",
    "#ff2277",
    "#ff1155",
    "#ff1133",
    "#ff1111",
)

_TITLE_LINES = (
    "███████╗███╗░░██╗███████╗",
    "╚════██║████╗░██║██╔════╝",
    "░░███╔═╝██╔██╗██║█████╗░░",
    "██╔══╝░░██║╚████║██╔══╝░░",
    "███████╗██║░╚███║███████╗",
    "╚══════╝╚═╝░░╚══╝╚══════╝",
)

_DIVIDER = "─" * 35


class _systemscreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "system.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    _monitor = resourcemonitor(interval=1.0)

    def compose(self) -> ComposeResult:
        with Vertical(id="sys-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"sys-logo-{i}")
            yield Label("SYSTEM", id="sys-subtitle")
        with VerticalScroll(id="sys-scroll"):
            yield Label("", id="sys-data")
        with Vertical(id="sys-footer"):
            yield Label("press esc to go back", id="sys-back-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        for k, char in enumerate(line):
            colour = _COLOURS[(k + offset) % 26]
            text.append(char, style=colour)
        return text

    def _section(self, title: str) -> Text:
        text = Text()
        text.append("── ", style="#7755cc")
        text.append(title, style="#aa88ff bold")
        text.append(" ", style="#7755cc")
        text.append(_DIVIDER, style="#7755cc")
        text.append("\n")
        return text

    def _bar(self, percent: float, width: int = 30) -> Text:
        filled = int(width * min(percent, 100) / 100)
        empty = width - filled
        if percent < 50:
            colour = "#44ff88"
        elif percent < 80:
            colour = "#ffcc22"
        else:
            colour = "#ff4444"
        text = Text()
        text.append("█" * filled + "░" * empty, style=colour)
        text.append(f" {percent:>5.1f}%", style="#ccccee")
        return text

    def _render_cpu(self) -> Text:
        stats = self._monitor.cpu()
        text = self._section("CPU")
        text.append(" Total   ", style="#9988bb")
        text.append(self._bar(stats.total_percent))
        text.append("\n")
        for i, pct in enumerate(stats.per_core):
            text.append(f" Core {i:<2}", style="#9988bb")
            text.append(self._bar(pct, width=20))
            text.append("\n")
        if stats.freq_current > 0:
            text.append(f" Freq: {stats.freq_current:.0f} MHz", style="#9988bb")
            if stats.freq_max > 0:
                text.append(f" (max {stats.freq_max:.0f})", style="#7755aa")
        return text

    def _render_mem(self) -> Text:
        stats = self._monitor.memory()
        text = self._section("Memory")
        text.append(" RAM     ", style="#9988bb")
        text.append(self._bar(stats.ram_percent))
        text.append(
            f"  {stats.ram_used_gb:.1f} / {stats.ram_total_gb:.1f} GB",
            style="#9988bb",
        )
        text.append("\n")
        text.append(" Swap    ", style="#9988bb")
        text.append(self._bar(stats.swap_percent, width=20))
        text.append(
            f"  {stats.swap_used_gb:.1f} / {stats.swap_total_gb:.1f} GB",
            style="#9988bb",
        )
        return text

    def _render_disk(self) -> Text:
        disks = self._monitor.disks()
        text = self._section("Disk")
        if not disks:
            text.append("  No partitions found", style="#554477")
            return text
        for d in disks:
            mount = d.mountpoint
            if len(mount) > 8:
                mount = mount[:7] + "…"
            text.append(f" {mount:<8}", style="#9988bb")
            text.append(self._bar(d.percent, width=20))
            text.append(
                f"  {d.used_gb:.0f}/{d.total_gb:.0f} GB [{d.fstype}]",
                style="#7755aa",
            )
            text.append("\n")
        return text

    def _render_net(self) -> Text:
        interfaces = self._monitor.network()
        conns = self._monitor.connections_count()
        text = self._section("Network")
        for nic in interfaces:
            if not nic.is_up:
                continue
            text.append(f" {nic.name:<10}", style="#9988bb")
            text.append(f"↑{nic.sent_mb:>8.1f} MB  ", style="#44ff88")
            text.append(f"↓{nic.recv_mb:>8.1f} MB", style="#ff8844")
            if nic.speed > 0:
                text.append(f"  {nic.speed} Mbps", style="#7755aa")
            text.append("\n")
        if conns >= 0:
            text.append(f" Connections: {conns}", style="#9988bb")
        else:
            text.append(" Connections: N/A (need root)", style="#554477")
        return text

    def _render_proc(self) -> Text:
        procs = self._monitor.processes(limit=8)
        text = self._section("Top Processes")
        text.append(" PID      ", style="#7755aa")
        text.append(f"{'NAME':<18}", style="#7755aa")
        text.append("  CPU%   RAM%\n", style="#7755aa")
        for p in procs:
            text.append(f" {p.pid:<8}", style="#9988bb")
            name = p.name[:16] if len(p.name) > 16 else p.name
            text.append(f"{name:<18}", style="#ccccee")
            text.append(f"{p.cpu_percent:>6.1f}  ", style="#ccccee")
            text.append(f"{p.ram_percent:>5.1f}", style="#ccccee")
            text.append("\n")
        return text

    def _format_uptime(self, seconds: float) -> str:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _render_sysinfo(self) -> Text:
        info = self._monitor.system()
        text = self._section("System")
        text.append(f" Platform: {info.system} {info.release}\n", style="#9988bb")
        text.append(f" Hostname: {info.hostname}\n", style="#9988bb")
        text.append(
            f" Uptime:   {self._format_uptime(info.uptime_seconds)}\n",
            style="#9988bb",
        )
        text.append(
            f" Users:    {', '.join(info.users) if info.users else 'none'}\n",
            style="#9988bb",
        )
        text.append(
            f" CPUs:     {info.cpu_logical} logical / {info.cpu_physical} physical",
            style="#9988bb",
        )
        return text

    def _render_sensors(self) -> Text:
        temps = self._monitor.temperatures()
        bat = self._monitor.battery()
        if not temps and bat is None:
            return Text()
        text = self._section("Sensors")
        for group_name, sensors in temps:
            for s in sensors:
                text.append(f" {s.label:<20}", style="#9988bb")
                text.append(f"{s.current:>5.0f}°C", style="#ccccee")
                if s.high > 0:
                    text.append(f" (high {s.high:.0f}°C", style="#7755aa")
                    if s.critical > 0:
                        text.append(f", crit {s.critical:.0f}°C", style="#ff4444")
                    text.append(")", style="#7755aa")
                text.append("\n")
        if bat is not None:
            text.append(" Battery:  ", style="#9988bb")
            text.append(f"{bat.percent:.0f}%", style="#ccccee")
            if bat.power_plugged:
                text.append(" (AC connected)", style="#7755aa")
            elif bat.secs_left > 0:
                hrs = int(bat.secs_left // 3600)
                mins = int((bat.secs_left % 3600) // 60)
                text.append(f" ({hrs}h {mins}m left)", style="#7755aa")
        return text

    async def on_mount(self) -> None:
        self._logo_labels = tuple(
            self.query_one(f"#sys-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._data_label = self.query_one("#sys-data", Label)
        self._back_hint = self.query_one("#sys-back-hint", Label)
        self.run_worker(self._animate_header())
        self.run_worker(self._update_stats())

    async def _animate_header(self) -> None:
        offset = 0
        while True:
            for i, line in enumerate(_TITLE_LINES):
                self._logo_labels[i].update(self._gradient_text(line, offset))
            offset = (offset + 1) % 26
            await asyncio.sleep(0.08)

    async def _update_stats(self) -> None:
        while True:
            content = Text()
            content.append(self._render_cpu())
            content.append("\n")
            content.append(self._render_mem())
            content.append("\n")
            content.append(self._render_disk())
            content.append("\n")
            content.append(self._render_net())
            content.append("\n")
            content.append(self._render_proc())
            content.append("\n")
            content.append(self._render_sysinfo())
            sensors = self._render_sensors()
            if sensors:
                content.append("\n")
                content.append(sensors)
            self._data_label.update(content)
            self._back_hint.update(
                self._gradient_text(
                    "press esc to go back",
                    offset=int(time.monotonic() * 12) % 26,
                )
            )
            await asyncio.sleep(1.0)
