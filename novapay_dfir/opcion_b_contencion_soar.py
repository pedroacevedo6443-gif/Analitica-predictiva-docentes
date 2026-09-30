#!/usr/bin/env python3
"""Opción B - Contención automatizada (SOAR/EDR) para el servidor de conciliación.

Diseño:
  * Simulación (dry-run) por defecto; solo actúa con --execute.
  * Orden: evidencia -> aislar red -> matar conector -> deshabilitar cuenta -> bloquear carpeta.
  * Todo es reversible (rollback) y queda registrado en un log JSONL.
  * Sin shell=True; entradas validadas con regex para evitar inyección de comandos.
Requiere Windows + PowerShell + privilegios de administrador para --execute.
"""
import argparse          # CLI
import csv               # parseo de tasklist
import hashlib           # hash del binario del conector
import io                # buffer para csv
import json              # log estructurado
import re                # validación de entradas
import subprocess        # ejecución de comandos sin shell
import sys               # salida/códigos de retorno
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Validadores estrictos: solo caracteres esperables en cada campo.
RE_PROC = re.compile(r"^[A-Za-z0-9_.\-]{1,64}\.exe$")
RE_ACCOUNT = re.compile(r"^[A-Za-z0-9_.\-\\$@]{1,64}$")
RE_IP = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


@dataclass
class Config:
    """Parámetros del incidente."""
    process_name: str       # ejecutable del conector PagoLink
    service_account: str    # cuenta de servicio a revocar (DOMINIO\\cuenta)
    folder: str             # carpeta de conciliación
    mgmt_ip: str            # única IP de gestión que conserva acceso
    evidence_dir: Path      # destino de evidencias y backups
    execute: bool           # False = solo simular


class Recorder:
    """Registra cada acción con marca UTC en JSONL (cadena de custodia básica)."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)   # crea carpeta de evidencias
        self.path = path

    def log(self, step: str, **data):
        rec = {"utc": datetime.now(timezone.utc).isoformat(), "step": step, **data}
        with self.path.open("a", encoding="utf-8") as fh:  # append: nunca sobrescribe
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{rec['utc']}] {step} {data}")


def validate(cfg: Config):
    """Rechaza configuraciones que podrían inyectar argumentos."""
    if not RE_PROC.match(cfg.process_name):
        raise ValueError("process_name inválido")
    if not RE_ACCOUNT.match(cfg.service_account):
        raise ValueError("service_account inválido")
    if not RE_IP.match(cfg.mgmt_ip) or any(int(o) > 255 for o in cfg.mgmt_ip.split(".")):
        raise ValueError("mgmt_ip inválida")
    if not cfg.folder or any(c in cfg.folder for c in '"\n\r;|&`'):
        raise ValueError("folder inválido")


def run(cfg: Config, rec: Recorder, step: str, argv: list, timeout=60) -> str:
    """Ejecuta (o simula) un comando; nunca lanza: devuelve '' si falla."""
    if not cfg.execute:
        rec.log(step, mode="dry-run", cmd=argv)
        return ""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        rec.log(step, rc=p.returncode, stdout=p.stdout[-2000:], stderr=p.stderr[-500:])
        return p.stdout
    except (OSError, subprocess.TimeoutExpired) as exc:   # binario ausente o cuelgue
        rec.log(step, error=str(exc))
        return ""


def ps(cfg, rec, step, script):
    """Atajo para invocar PowerShell sin perfil ni interacción."""
    return run(cfg, rec, step, ["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


# ---------------------------------------------------------------- pasos ----
def collect_evidence(cfg, rec):
    """Captura volátil mínima ANTES de contener (procesos, conexiones, ACL, hash)."""
    d = cfg.evidence_dir
    ps(cfg, rec, "evid_proc", f"Get-CimInstance Win32_Process -Filter \"Name='{cfg.process_name}'\" | "
       f"Select ProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json | Out-File '{d}\\proc.json'")
    run(cfg, rec, "evid_netstat", ["cmd", "/c", f"netstat -ano > \"{d}\\netstat.txt\""])
    run(cfg, rec, "evid_acl", ["icacls", cfg.folder, "/save", str(d / "acl_backup.txt"), "/t", "/c"])
    if cfg.execute:  # hash del binario para IoC/atribución
        out = ps(cfg, rec, "evid_path", f"(Get-Process {cfg.process_name[:-4]} -ErrorAction SilentlyContinue | "
                 "Select -First 1).Path")
        exe = Path(out.strip()) if out.strip() else None
        if exe and exe.is_file():
            rec.log("evid_sha256", path=str(exe), sha256=hashlib.sha256(exe.read_bytes()).hexdigest())


def isolate_network(cfg, rec):
    """Política de firewall bloquear-todo, con excepción solo para la IP de gestión."""
    run(cfg, rec, "fw_backup", ["netsh", "advfirewall", "export", str(cfg.evidence_dir / "fw_backup.wfw")])
    run(cfg, rec, "fw_allow_in", ["netsh", "advfirewall", "firewall", "add", "rule", "name=IR-ALLOW-MGMT-IN",
        "dir=in", "action=allow", f"remoteip={cfg.mgmt_ip}", "enable=yes", "profile=any"])
    run(cfg, rec, "fw_allow_out", ["netsh", "advfirewall", "firewall", "add", "rule", "name=IR-ALLOW-MGMT-OUT",
        "dir=out", "action=allow", f"remoteip={cfg.mgmt_ip}", "enable=yes", "profile=any"])
    run(cfg, rec, "fw_block_all", ["netsh", "advfirewall", "set", "allprofiles", "firewallpolicy",
        "blockinbound,blockoutbound"])


def kill_connector(cfg, rec):
    """Termina el conector y su árbol de procesos (evidencia ya capturada)."""
    out = run(cfg, rec, "list_proc", ["tasklist", "/FO", "CSV", "/NH", "/FI", f"IMAGENAME eq {cfg.process_name}"])
    for row in csv.reader(io.StringIO(out)):
        if len(row) > 1 and row[1].isdigit():                       # columna PID
            run(cfg, rec, "kill", ["taskkill", "/PID", row[1], "/F", "/T"])
    if not cfg.execute:
        run(cfg, rec, "kill", ["taskkill", "/IM", cfg.process_name, "/F", "/T"])


def revoke_account(cfg, rec):
    """Deshabilita la cuenta (AD si está disponible; si no, cuenta local)."""
    acct = cfg.service_account
    ps(cfg, rec, "disable_account",
       f"if (Get-Command Disable-ADAccount -ErrorAction SilentlyContinue) "
       f"{{ Disable-ADAccount -Identity '{acct.split(chr(92))[-1]}' }} "
       f"else {{ net user '{acct.split(chr(92))[-1]}' /active:no }}")


def lock_folder(cfg, rec):
    """Niega escritura/borrado a la cuenta de servicio; conserva lectura para forense."""
    run(cfg, rec, "acl_deny", ["icacls", cfg.folder, "/deny", f"{cfg.service_account}:(OI)(CI)(W,D,DC)"])


def rollback(cfg, rec):
    """Revierte firewall y ACL (la cuenta se rehabilita manualmente tras rotar credenciales)."""
    run(cfg, rec, "fw_restore", ["netsh", "advfirewall", "import", str(cfg.evidence_dir / "fw_backup.wfw")])
    run(cfg, rec, "acl_restore", ["icacls", str(Path(cfg.folder).parent), "/restore",
                                  str(cfg.evidence_dir / "acl_backup.txt")])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--process", required=True, help="p.ej. PagoLinkConnector.exe")
    ap.add_argument("--account", required=True, help="DOMINIO\\svc_pagolink")
    ap.add_argument("--folder", required=True)
    ap.add_argument("--mgmt-ip", required=True)
    ap.add_argument("--evidence-dir", default="evidencia_novapay")
    ap.add_argument("--execute", action="store_true", help="aplicar cambios reales")
    ap.add_argument("--rollback", action="store_true")
    a = ap.parse_args()
    cfg = Config(a.process, a.account, a.folder, a.mgmt_ip, Path(a.evidence_dir), a.execute)
    try:
        validate(cfg)
        rec = Recorder(cfg.evidence_dir / "acciones.jsonl")
    except (ValueError, OSError) as exc:
        sys.exit(f"Configuración inválida: {exc}")
    if cfg.execute and sys.platform != "win32":
        sys.exit("--execute requiere Windows")
    cfg.evidence_dir.mkdir(parents=True, exist_ok=True)
    if a.rollback:
        rollback(cfg, rec)
        return
    for step in (collect_evidence, isolate_network, kill_connector, revoke_account, lock_folder):
        try:
            step(cfg, rec)                      # un fallo no debe detener la contención
        except Exception as exc:                # noqa: BLE001 - robustez ante fallos parciales
            rec.log(step.__name__, error=repr(exc))
    rec.log("done", mode="EXECUTE" if cfg.execute else "DRY-RUN")


if __name__ == "__main__":
    main()
