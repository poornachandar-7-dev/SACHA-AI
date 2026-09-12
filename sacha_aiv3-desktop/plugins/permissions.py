"""
plugins/permissions.py — permission flags (fs, network, exec, mic, cam).

Permissions are a whitelist model: everything a plugin can do must be
declared in plugin.json. ``unknown`` flags are rejected at load time.
"""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    FS = "fs"            # read/write user files under data/
    NETWORK = "network"  # outbound HTTP
    EXEC = "exec"        # spawn processes (never auto-granted)
    MIC = "mic"          # record audio from the microphone
    CAM = "cam"          # access the camera
    CLI = "cli"          # read clipboard / system info


KNOWN_PERMISSIONS = frozenset(p.value for p in Permission)

PERMISSION_DOC: dict[str, str] = {
    Permission.FS.value: "Files — can read/write files under the user's data folder.",
    Permission.NETWORK.value: "Network — can make outbound HTTP requests.",
    Permission.EXEC.value: "Exec — can spawn external programs. High risk; ask the user.",
    Permission.MIC.value: "Microphone — can capture audio for wake word / STT.",
    Permission.CAM.value: "Camera — can access a camera feed.",
    Permission.CLI.value: "Clipboard — can read or write the clipboard.",
}


def known_permission(name: str | Permission) -> bool:
    """True when ``name`` is a declared permission."""
    return Permission(name) in Permission if isinstance(name, Permission) else name in KNOWN_PERMISSIONS


def describe_permission(name: str) -> str:
    return PERMISSION_DOC.get(name, name)
