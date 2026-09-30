#!/usr/bin/env python3
"""Opción C - FIM en tiempo real con watchdog (pip install watchdog).

Nota: watchdog NO puede bloquear escrituras (el kernel ya las aceptó); detecta
y reacciona. Para bloqueo real se requiere ACL/minifiltro/EDR (ver Opción B).
"""
import argparse, subprocess, sys, time, threading
from collections import deque
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

LIMIT, WINDOW = 50, 60.0


class MassChangeHandler(FileSystemEventHandler):
    def __init__(self, on_trigger):
        self.events, self.lock, self.on_trigger, self.tripped = deque(), threading.Lock(), on_trigger, False

    def on_any_event(self, event):
        if event.is_directory:
            return
        now = time.monotonic()
        with self.lock:
            self.events.append(now)
            while self.events and now - self.events[0] > WINDOW:
                self.events.popleft()
            if len(self.events) > LIMIT and not self.tripped:
                self.tripped = True
                self.on_trigger(len(self.events), event.src_path)


def react(count, path, deny_account, folder, execute):
    print(f"[ALERTA] {count} cambios/min; último: {path}", flush=True)
    cmd = ["icacls", folder, "/deny", f"{deny_account}:(OI)(CI)(W,D,DC)"]
    if execute:
        try:
            subprocess.run(cmd, check=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"[error] no se pudo aplicar ACL: {exc}", file=sys.stderr)
    else:
        print("[dry-run]", " ".join(cmd))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--service-account", required=True)
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    handler = MassChangeHandler(lambda c, p: react(c, p, a.service_account, a.folder, a.execute))
    obs = Observer()
    obs.schedule(handler, a.folder, recursive=True)
    obs.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        obs.stop(); obs.join()


if __name__ == "__main__":
    main()
