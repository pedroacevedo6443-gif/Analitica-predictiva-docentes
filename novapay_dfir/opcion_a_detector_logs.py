#!/usr/bin/env python3
"""Opción A - Detector de exfiltración y modificación masiva (solo detección).

Entradas:
  --net   CSV de red:        timestamp_iso,src_ip,dst_ip,dst_port,bytes_out
  --fs    CSV de archivos:   timestamp_iso,path,action,account
  --allow archivo con IPs/CIDR documentados (uno por línea, # comentarios)
"""
import argparse, csv, ipaddress, sys
from collections import defaultdict, deque
from datetime import datetime, timedelta

MAX_FILES_PER_MIN = 50  # umbral definido en el caso


def load_allowlist(path):
    """Lee redes permitidas; falla cerrado si el archivo no existe."""
    nets = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#")[0].strip()
            if line:
                nets.append(ipaddress.ip_network(line, strict=False))
    return nets


def is_documented(ip, nets):
    """True si la IP es privada/loopback o está en la lista documentada."""
    addr = ipaddress.ip_address(ip)
    return addr.is_private or addr.is_loopback or any(addr in n for n in nets)


def detect_exfil(net_csv, nets):
    """Devuelve alertas por conexiones salientes a destinos no documentados."""
    alerts, totals = [], defaultdict(int)
    with open(net_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                if not is_documented(row["dst_ip"], nets):
                    totals[(row["src_ip"], row["dst_ip"])] += int(row["bytes_out"])
                    alerts.append(("EXFIL", row["timestamp_iso"], row["src_ip"],
                                   row["dst_ip"], row["dst_port"]))
            except (KeyError, ValueError) as exc:
                print(f"[warn] fila de red inválida: {exc}", file=sys.stderr)
    return alerts, totals


def detect_mass_change(fs_csv):
    """Ventana deslizante de 60 s: alerta si supera MAX_FILES_PER_MIN eventos."""
    window, alerts, fired = deque(), [], False
    with open(fs_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                ts = datetime.fromisoformat(row["timestamp_iso"])
            except (KeyError, ValueError) as exc:
                print(f"[warn] fila de archivos inválida: {exc}", file=sys.stderr)
                continue
            window.append(ts)
            while window and ts - window[0] > timedelta(seconds=60):
                window.popleft()
            if len(window) > MAX_FILES_PER_MIN and not fired:
                alerts.append(("MASS_CHANGE", ts.isoformat(), len(window), row.get("account", "?")))
                fired = True  # una alerta por ráfaga
            elif len(window) <= MAX_FILES_PER_MIN:
                fired = False
    return alerts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", required=True)
    ap.add_argument("--fs", required=True)
    ap.add_argument("--allow", required=True)
    a = ap.parse_args()
    try:
        nets = load_allowlist(a.allow)
        exfil, totals = detect_exfil(a.net, nets)
        mass = detect_mass_change(a.fs)
    except OSError as exc:
        sys.exit(f"Error de E/S: {exc}")
    for al in exfil + mass:
        print("ALERTA", *al)
    for (src, dst), b in totals.items():
        print(f"RESUMEN {src} -> {dst}: {b} bytes")
    sys.exit(2 if (exfil or mass) else 0)


if __name__ == "__main__":
    main()
