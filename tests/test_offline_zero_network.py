"""Zero-network harness for geni_offline/ (slice 3 of #93).

Two independent guards:
1. A static AST scan forbids network, subprocess and dynamic-import modules,
   the two CLI modules, and process-spawning os calls.
2. Every geni_offline module is imported in a child interpreter with an audit
   hook that raises on socket, urllib, http.client, subprocess, os.system,
   exec and spawn events.

Each guard has a self-test with planted violations, so a guard that silently
stops working fails here too. Synthetic inputs only; nothing touches the network.
"""
import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "geni_offline"

FORBIDDEN_MODULES = frozenset({
    "socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp", "asyncio",
    "socketserver", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "xmlrpc",
    "webbrowser", "subprocess", "multiprocessing", "pty", "ctypes", "importlib",
    "geni_upload", "source_details",
})
FORBIDDEN_CALLS = frozenset({"__import__", "exec", "eval", "compile"})
FORBIDDEN_OS_ATTRS = frozenset({
    "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
    "execv", "execve", "execl", "execle", "execlp", "execlpe", "execvp", "execvpe",
    "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp",
    "spawnvpe",
})


def violations(source, filename="<planted>"):
    """Return a sorted list of 'line:reason' strings for forbidden constructs."""
    found = []
    for node in ast.walk(ast.parse(source, filename)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    found.append(f"{node.lineno}:import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and (node.module or "").split(".")[0] in FORBIDDEN_MODULES:
                found.append(f"{node.lineno}:from {node.module}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                found.append(f"{node.lineno}:call {func.id}")
        if (isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_OS_ATTRS
                and isinstance(node.value, ast.Name) and node.value.id == "os"):
            found.append(f"{node.lineno}:os.{node.attr}")
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if alias.name in FORBIDDEN_OS_ATTRS:
                    found.append(f"{node.lineno}:from os import {alias.name}")
    return sorted(found)


def package_files():
    return sorted(PACKAGE.rglob("*.py"))


# --- static guard -----------------------------------------------------------

def test_package_exists_and_is_scanned():
    files = package_files()
    assert PACKAGE / "__init__.py" in files


@pytest.mark.parametrize("path", package_files(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_package_has_no_forbidden_constructs(path):
    assert violations(path.read_text(encoding="utf-8"), str(path)) == []


def test_package_contains_no_native_or_symlinked_code():
    for path in PACKAGE.rglob("*"):
        assert not path.is_symlink(), path.relative_to(ROOT)
        assert path.suffix not in {".so", ".pyd", ".dll", ".dylib"}, path.relative_to(ROOT)


@pytest.mark.parametrize("source, expected", [
    ("import socket", "1:import socket"),
    ("import urllib.request", "1:import urllib.request"),
    ("from http import client", "1:from http"),
    ("from http.client import HTTPSConnection", "1:from http.client"),
    ("import subprocess as sp", "1:import subprocess"),
    ("import geni_upload", "1:import geni_upload"),
    ("from source_details import main", "1:from source_details"),
    ("import importlib\nimportlib.import_module('x')", "1:import importlib"),
    ("__import__('socket')", "1:call __import__"),
    ("exec('pass')", "1:call exec"),
    ("import os\nos.system('true')", "2:os.system"),
    ("import os\nos.posix_spawn", "2:os.posix_spawn"),
    ("from os import popen", "1:from os import popen"),
])
def test_static_guard_flags_planted_violation(source, expected):
    assert expected in violations(source)


@pytest.mark.parametrize("source", [
    "import json\nimport os\nos.open('x', os.O_RDONLY)",
    "from . import sibling",
    "from .net import thing",  # relative import inside the package is allowed
    "import hashlib, stat, pathlib",
    "socket = 1",  # a name, not an import
])
def test_static_guard_allows_clean_source(source):
    assert violations(source) == []


# --- runtime guard ----------------------------------------------------------

HOOK = textwrap.dedent("""
    import sys
    BLOCKED = {
        "urllib.Request", "http.client.connect", "http.client.send",
        "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn",
        "os.spawn", "os.fork", "os.forkpty", "ctypes.dlopen",
        "ftplib.connect", "smtplib.connect", "webbrowser.open",
    }
    def _hook(event, args):
        if event in BLOCKED or event.startswith("socket."):
            raise RuntimeError("BLOCKED:" + event)
    sys.addaudithook(_hook)
""")

IMPORT_PACKAGE = textwrap.dedent("""
    sys.path.insert(0, ROOT)
    import pkgutil
    import geni_offline
    names = [m.name for m in pkgutil.walk_packages(geni_offline.__path__, "geni_offline.")]
    for name in names:
        __import__(name)
    print("imported", 1 + len(names))
""")


def run_guarded(payload):
    code = f"ROOT = {str(ROOT)!r}\n" + HOOK + payload
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True, text=True, timeout=60, env=env, check=False,
    )


def test_every_package_module_imports_under_the_network_hook():
    result = run_guarded(IMPORT_PACKAGE)
    assert result.returncode == 0, result.stderr
    assert "BLOCKED:" not in result.stderr
    assert result.stdout.startswith("imported ")


@pytest.mark.parametrize("payload, event", [
    ("import socket\nsocket.socket()", "socket.__new__"),
    ("import socket\nsocket.getaddrinfo('localhost', 9)", "socket.getaddrinfo"),
    ("import urllib.request\nurllib.request.urlopen('http://127.0.0.1:9/')", "urllib.Request"),
    ("import subprocess\nsubprocess.Popen(['true'])", "subprocess.Popen"),
    ("import os\nos.system('true')", "os.system"),
])
def test_runtime_guard_blocks_planted_call(payload, event):
    result = run_guarded(payload)
    assert result.returncode != 0
    assert f"BLOCKED:{event}" in result.stderr


def test_runtime_guard_allows_clean_payload():
    result = run_guarded("import json\nprint(json.dumps({'ok': True}))")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '{"ok": true}'


def test_child_environment_carries_no_credentials(monkeypatch):
    monkeypatch.setenv("GENI_ACCESS_TOKEN", "synthetic-not-a-token")
    monkeypatch.setenv("GH_TOKEN", "synthetic-not-a-token")
    result = run_guarded(
        "import os\nprint(sorted(k for k in os.environ if 'TOKEN' in k or 'GENI' in k))"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"
