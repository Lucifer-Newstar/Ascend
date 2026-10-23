"""What this PC can run: total RAM and, when an NVIDIA GPU is present, its VRAM.

Both are read locally (the OS and the GPU driver's own nvidia-smi); nothing leaves the PC.
AMD and Intel GPUs report no VRAM here, so the recommendation falls back to RAM.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Hardware:
    ram_gb: float | None
    vram_gb: float | None
    gpu: str | None


def _ram_bytes() -> int | None:
    if sys.platform == "win32":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        st = MemoryStatus()
        st.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):  # type: ignore[attr-defined]
            return int(st.ullTotalPhys)
        return None
    try:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (ValueError, OSError, AttributeError):
        return None


def _nvidia() -> tuple[float | None, str | None]:
    exe = shutil.which("nvidia-smi")
    if exe is None:
        return None, None
    try:
        out = subprocess.run(
            [exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=4,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    best: tuple[float | None, str | None] = (None, None)
    for line in out.strip().splitlines():
        name, _, mib = line.rpartition(",")
        try:
            gb = round(float(mib) / 1024, 1)
        except ValueError:
            continue
        if best[0] is None or gb > best[0]:
            best = (gb, name.strip())
    return best


def detect() -> Hardware:
    ram = _ram_bytes()
    vram, gpu = _nvidia()
    return Hardware(round(ram / 1024**3, 1) if ram else None, vram, gpu)


def ollama_installed() -> bool:
    """Whether the Ollama program is on this PC (it may still be stopped)."""
    if shutil.which("ollama"):
        return True
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return False
    return (Path(local) / "Programs" / "Ollama" / "ollama.exe").exists()
