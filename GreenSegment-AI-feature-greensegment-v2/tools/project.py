"""Local project commands; paths are resolved independently of the current directory."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import venv

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
LOCAL = ROOT / ".local"
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
os.environ.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PIP_DISABLE_PIP_VERSION_CHECK="1")
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def require_tool(name):
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"Missing {name}. Install Python 3.14 and Node.js 24, then reopen the terminal.")
    return executable


def run(args, *, cwd=ROOT):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def setup():
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError("Use Python 3.14 for the pinned development environment.")
    require_tool("node")
    npm = require_tool("npm.cmd" if os.name == "nt" else "npm")
    if not PYTHON.exists():
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    run([PYTHON, "-m", "pip", "install", "-r", "requirements-lock.txt"])
    run([npm, "ci", "--no-audit", "--no-fund"], cwd=WEB)
    ensure_env()
    print("Setup complete. Run: project.ps1 dev", flush=True)


def ensure_env():
    if not (ROOT / ".env").exists():
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")


def commands():
    if not PYTHON.exists():
        raise RuntimeError("Missing .venv. Run the setup command first.")
    vite = WEB / "node_modules/vite/bin/vite.js"
    if not vite.exists():
        raise RuntimeError("Missing frontend dependencies. Run the setup command first.")
    ensure_env()
    backend = [str(PYTHON), "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1",
               "--port", "8000", "--reload", "--reload-dir", "api", "--reload-dir", "src",
               "--env-file", ".env"]
    frontend = [require_tool("node"), str(vite), "--host", "127.0.0.1", "--port", "5173", "--strictPort"]
    return backend, frontend


def check():
    commands()
    run([PYTHON, "-m", "pip", "check"])
    LOCAL.mkdir(exist_ok=True)
    log = LOCAL / "tests.log"
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run([str(PYTHON), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                                cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    print("\n".join(log.read_text(encoding="utf-8").splitlines()[-(30 if result.returncode else 5):]), flush=True)
    if result.returncode:
        raise RuntimeError(f"Tests failed. Details: {log}")
    run([PYTHON, "-c", "import numpy, pandas, scipy, sklearn, matplotlib, joblib; print('ML imports: OK')"])
    run([require_tool("npm.cmd" if os.name == "nt" else "npm"), "run", "build"], cwd=WEB)


def get(url):
    with urlopen(url, timeout=3) as response:
        return response.read()


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        # Kill only this launcher's process tree, including Uvicorn's reload worker.
        result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode and process.poll() is None:
            raise RuntimeError(f"Cannot stop process tree {process.pid}. Check terminal process permissions.")
    else:
        import signal
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@contextmanager
def services(*, preview=False, frontend_only=False, port=5173):
    backend, frontend = commands()
    frontend[frontend.index("--port") + 1] = str(port)
    if preview:
        frontend.insert(2, "preview")
    for service_port in ((port,) if frontend_only else (8000, port)):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", service_port)) == 0:
                raise RuntimeError(f"Port {service_port} is already in use. Stop the previous service first.")
    LOCAL.mkdir(exist_ok=True)
    processes, logs = [], []
    try:
        launches = [("ui-preview" if frontend_only else "frontend", frontend, WEB)]
        if not frontend_only:
            launches.insert(0, ("backend", backend, ROOT))
        for name, command, cwd in launches:
            log = (LOCAL / f"{name}.log").open("w", encoding="utf-8")
            logs.append(log)
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            processes.append(subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, **options))
        deadline = time.monotonic() + 45
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError(f"A service exited during startup. See logs in {LOCAL}")
            try:
                health = {"ok": True} if frontend_only else json.loads(get("http://127.0.0.1:8000/api/health"))
                get(f"http://127.0.0.1:{port}/")
                if not health.get("ok"):
                    raise RuntimeError("Backend reports missing data files.")
                break
            except (URLError, TimeoutError, ConnectionError):
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Startup timed out. See logs in {LOCAL}") from None
                time.sleep(0.25)
        print(f"Web: http://127.0.0.1:{port}", flush=True)
        print("Logs: .local/ui-preview.log" if frontend_only else "API docs: http://127.0.0.1:8000/docs\nLogs: .local/backend.log and .local/frontend.log", flush=True)
        yield processes
    finally:
        failures = []
        for process in reversed(processes):
            try:
                stop(process)
            except RuntimeError as exc:
                failures.append(str(exc))
        for log in logs:
            log.close()
        if failures:
            raise RuntimeError("; ".join(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "dev", "backend", "frontend", "check", "smoke", "ui"], default="dev", nargs="?")
    action = parser.parse_args().action
    if action == "setup":
        setup()
    elif action == "check":
        check()
    elif action in ("backend", "frontend"):
        backend, frontend = commands()
        run(backend if action == "backend" else frontend, cwd=ROOT if action == "backend" else WEB)
    else:
        if action == "ui":
            run([require_tool("npm.cmd" if os.name == "nt" else "npm"), "run", "build"], cwd=WEB)
        with services(preview=action == "ui", frontend_only=action == "ui", port=5175 if action == "ui" else 5173) as processes:
            if action == "smoke":
                assert json.loads(get("http://127.0.0.1:5173/api/health"))["ok"]
                cities = json.loads(get("http://127.0.0.1:5173/api/cities?search=Nagoya"))
                assert cities["total"] > 0
                overview = json.loads(get("http://127.0.0.1:5173/api/overview"))
                print(f"HTTP checks: frontend, proxy, health, city search and overview OK ({len(overview)} overview fields).", flush=True)
            elif action == "ui":
                os.environ["MARKET_UI_URL"] = "http://127.0.0.1:5175"
                os.environ["OVERVIEW_UI_URL"] = "http://127.0.0.1:5175"
                run([PYTHON, "tests/ui_overview.py"])
                run([PYTHON, "tests/ui_market_search.py"])
            else:
                print("Press Ctrl+C to stop both services.", flush=True)
                while all(process.poll() is None for process in processes):
                    time.sleep(0.5)
                raise RuntimeError(f"A service stopped. See logs in {LOCAL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServices stopped.")
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
