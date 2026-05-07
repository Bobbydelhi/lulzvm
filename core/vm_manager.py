"""
VM Manager — Enterprise-grade lifecycle manager.
Handles QEMU process execution, robust state tracking, strict error handling and automated cleanup.
"""
import asyncio
import json
import logging
import os
import signal
import subprocess
import tomllib
import tomli_w
from pathlib import Path
import psutil
from typing import Optional, Dict, Any, List

from config import settings
from core.qmp_client import QMPClient, QMPError
from core.network import NetworkManager
from core.storage import StorageManager

logger = logging.getLogger("lulzvm.vm")


class VMManager:

    def __init__(self):
        self.config_dir  = Path(settings.paths.config_dir) / "vms"
        self.run_dir     = Path(settings.paths.run_dir)
        self.log_dir     = Path(settings.paths.log_dir) / "vms"
        self.net_manager = NetworkManager()
        self.store       = StorageManager()

    # ── CRUD de configuración ───────────────────────────────────────────────

    def load_config(self, vmid: int) -> dict:
        path = self.config_dir / f"{vmid}.toml"
        if not path.exists():
            raise FileNotFoundError(f"VM {vmid} not found in configuration.")
        with open(path, "rb") as f:
            return tomllib.load(f)

    def save_config(self, vmid: int, config: dict) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        path = self.config_dir / f"{vmid}.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)

    def list_vms(self) -> list:
        vms = []
        if not self.config_dir.exists():
            return vms
        for toml_file in self.config_dir.glob("*.toml"):
            try:
                with open(toml_file, "rb") as f:
                    cfg = tomllib.load(f)
                vms.append(cfg)
            except Exception as e:
                logger.warning(f"Corrupted config {toml_file}: {e}")
        return vms

    def create_vm(self, vmid: int, name: str, memory_mb: int, cores: int,
                  cpu_type: str = "host", machine: str = "q35",
                  bios: str = "seabios", cdrom: str = "",
                  disks: list = None, nics: list = None,
                  onboot: bool = False) -> dict:
        from datetime import datetime
        import random

        if (self.config_dir / f"{vmid}.toml").exists():
            raise ValueError(f"VM {vmid} already exists.")

        config = {
            "vm": {
                "vmid": vmid, "name": name, "status": "stopped",
                "created": datetime.utcnow().isoformat()
            },
            "hardware": {
                "memory_mb": memory_mb, "cores": cores, "sockets": 1,
                "cpu_type": cpu_type, "machine": machine, "bios": bios,
                "disks": disks or [],
                "nics": nics or [{
                    "id": "net0", "model": "virtio", "bridge": settings.defaults.default_bridge,
                    "mac": "AA:BB:CC:%02X:%02X:%02X" % (
                        random.randint(0,255), random.randint(0,255), random.randint(0,255)),
                    "vlan": 0
                }]
            },
            "boot": {"order": ["scsi0"], "cdrom": cdrom or ""},
            "options": {"onboot": onboot, "agent": False, "tablet": True, "vnc_port": 5900 + vmid}
        }
        self.save_config(vmid, config)
        logger.info(f"Created VM {vmid} ({name}) successfully.")
        return config

    def get_status(self, vmid: int) -> str:
        """Determina si la VM está corriendo verificando el proceso real."""
        pid = self._get_qemu_pid(vmid)
        if pid:
            return "running"
        return "stopped"

    def _get_qemu_pid(self, vmid: int) -> int:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'qemu-system' in proc.info['name']:
                    cmd = " ".join(proc.info['cmdline'] or [])
                    if f"qmp-{vmid}.sock" in cmd:
                        return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def delete_vm(self, vmid: int) -> None:
        if self.get_status(vmid) == "running":
            raise RuntimeError(f"VM {vmid} is currently running. You must stop it before deletion.")
        config_path = self.config_dir / f"{vmid}.toml"
        config_path.unlink(missing_ok=True)
        logger.info(f"Deleted VM {vmid} configuration.")

    # ── QEMU command builder ────────────────────────────────────────────────

    def _build_qemu_cmd(self, config: dict) -> list:
        hw  = config["hardware"]
        opt = config["options"]
        vmid = config["vm"]["vmid"]

        qmp_sock    = str(self.run_dir / f"qmp-{vmid}.sock")
        serial_sock = str(self.run_dir / f"serial-{vmid}.sock")
        log_file    = str(self.log_dir / f"{vmid}.log")

        accel = "kvm" if os.path.exists("/dev/kvm") else "tcg"
        cpu_type = hw["cpu_type"]
        if accel == "tcg" and cpu_type == "host":
            cpu_type = "max"

        cmd = [
            "qemu-system-x86_64",
            "-nodefaults",
            "-no-user-config",
            "-chardev", f"socket,id=charmonitor,path={qmp_sock},server=on,wait=off",
            "-mon",     "chardev=charmonitor,id=monitor,mode=control",
            "-machine", f"{hw['machine']},accel={accel}",
            "-cpu",     cpu_type,
            "-smp",     f"{hw['cores']},sockets={hw['sockets']},cores={hw['cores']},maxcpus={hw['cores']}",
            "-m",       str(hw["memory_mb"]),
            "-rtc",     "base=utc,driftfix=slew",
            "-global",  "kvm-pit.lost_tick_policy=discard",
            "-D",       log_file,
            "-chardev", f"socket,id=charserial0,path={serial_sock},server=on,wait=off",
            "-device",  "isa-serial,chardev=charserial0,id=serial0",
        ]

        if hw.get("bios") == "ovmf":
            ovmf_code = "/usr/share/OVMF/OVMF_CODE.fd"
            ovmf_vars = str(self.run_dir / f"ovmf-vars-{vmid}.fd")
            if not os.path.exists(ovmf_vars) and os.path.exists("/usr/share/OVMF/OVMF_VARS.fd"):
                import shutil
                shutil.copy("/usr/share/OVMF/OVMF_VARS.fd", ovmf_vars)
            cmd += [
                "-drive", f"if=pflash,unit=0,format=raw,readonly=on,file={ovmf_code}",
                "-drive", f"if=pflash,unit=1,format=raw,file={ovmf_vars}",
            ]

        # Display and UX Enhancements
        cmd += ["-vga", "std"]  # Ensure standard VGA is always injected for correct VNC rendering
        cmd += ["-k", "en-us"]  # Set default keyboard layout
        if opt.get("tablet"):
            cmd += ["-device", "usb-ehci,id=ehci", "-device", "usb-tablet,bus=ehci.0"]

        has_scsi = any(d.get("bus") in ("scsi", "virtio-scsi") for d in hw.get("disks", []))
        if has_scsi:
            cmd += ["-device", "virtio-scsi-pci,id=scsihw0,num_queues=4"]

        for disk in hw.get("disks", []):
            disk_path = self.store.get_disk_path(disk["storage"], disk["file"])
            if not os.path.exists(disk_path):
                raise FileNotFoundError(f"Virtual disk not found: {disk_path}")
            disk_fmt  = "qcow2" if disk["file"].endswith(".qcow2") else "raw"
            drive_id  = f"drive-{disk['id']}"
            cmd += [
                "-drive",  f"if=none,id={drive_id},format={disk_fmt},file={disk_path},cache={disk['cache']},aio={disk['aio']}",
                "-device", f"virtio-blk-pci,drive={drive_id},id={disk['id']},bootindex=1",
            ]

        cdrom = config.get("boot", {}).get("cdrom", "")
        if cdrom:
            if not os.path.exists(cdrom):
                raise FileNotFoundError(f"CDROM ISO not found: {cdrom}")
            cmd += ["-cdrom", cdrom, "-boot", "order=dc"]

        for nic in hw.get("nics", []):
            tap_name = f"tap{vmid}i{nic['id'][-1]}"
            cmd += [
                "-netdev", f"tap,id={nic['id']},ifname={tap_name},script=no,downscript=no",
                "-device", f"virtio-net-pci,netdev={nic['id']},mac={nic['mac']},id={nic['id']}-dev",
            ]

        vnc_port = opt.get("vnc_port", 5900 + vmid) - 5900
        cmd += ["-vnc", f":{vnc_port}"]
        cmd += ["-daemonize"]

        return cmd

    def update_vm(self, vmid: int, **kwargs) -> dict:
        config = self.load_config(vmid)
        if "name" in kwargs and kwargs["name"] is not None:
            config["vm"]["name"] = kwargs["name"]
        if "memory_mb" in kwargs and kwargs["memory_mb"] is not None:
            config["hardware"]["memory_mb"] = kwargs["memory_mb"]
        if "cores" in kwargs and kwargs["cores"] is not None:
            config["hardware"]["cores"] = kwargs["cores"]
        if "cdrom" in kwargs:
            config["boot"]["cdrom"] = kwargs["cdrom"] or ""
        if "onboot" in kwargs and kwargs["onboot"] is not None:
            config["options"]["onboot"] = kwargs["onboot"]
            
        self.save_config(vmid, config)
        return config

    # ── Lifecycle ───────────────────────────────────────────────────────────

    async def start(self, vmid: int) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Kill orphan zombies unconditionally
        pid = self._get_qemu_pid(vmid)
        if pid:
            logger.warning(f"VM {vmid}: Found rogue QEMU process (PID {pid}). Terminating.")
            os.kill(pid, 9)
            await asyncio.sleep(1)

        config = self.load_config(vmid)
        hw = config["hardware"]

        # Track created taps to clean them up if QEMU fails
        created_taps = []
        try:
            for nic in hw.get("nics", []):
                tap_name = f"tap{vmid}i{nic['id'][-1]}"
                await self.net_manager.create_tap(tap_name, nic["bridge"])
                created_taps.append(tap_name)

            cmd = self._build_qemu_cmd(config)
            logger.info(f"VM {vmid}: Executing QEMU -> {' '.join(cmd)}")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                err_text = stderr.decode().strip()
                raise RuntimeError(f"QEMU execution failed: {err_text}")

            # Verify QMP socket with timeout (Prevent zombie run)
            qmp_sock = str(self.run_dir / f"qmp-{vmid}.sock")
            for _ in range(30):
                if os.path.exists(qmp_sock):
                    break
                await asyncio.sleep(0.5)
            else:
                # If timeout, QEMU is hung. Kill it.
                pid = self._get_qemu_pid(vmid)
                if pid: os.kill(pid, 9)
                raise RuntimeError("QMP socket never appeared. QEMU process hung and was terminated.")

            config["vm"]["status"] = "running"
            self.save_config(vmid, config)
            logger.info(f"VM {vmid}: Started successfully.")

        except Exception as e:
            # Cleanup resources if initialization fails
            logger.error(f"VM {vmid} startup failed: {e}")
            for tap in created_taps:
                try:
                    await self.net_manager.delete_tap(tap)
                except Exception as ex:
                    logger.warning(f"Failed to cleanup tap {tap}: {ex}")
            config["vm"]["status"] = "error"
            self.save_config(vmid, config)
            raise

    async def stop(self, vmid: int, force: bool = False) -> None:
        if self.get_status(vmid) != "running":
            raise RuntimeError(f"VM {vmid} is not running.")

        pid = self._get_qemu_pid(vmid)
        if force:
            if pid:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"VM {vmid}: Force killed (PID {pid}).")
        else:
            qmp = await self._get_qmp(vmid)
            try:
                await qmp.system_powerdown()
                logger.info(f"VM {vmid}: ACPI powerdown requested. Waiting for exit...")
            except Exception as e:
                logger.error(f"VM {vmid}: ACPI signal failed: {e}. Falling back to SIGKILL.")
                if pid: os.kill(pid, signal.SIGKILL)
            finally:
                await qmp.disconnect()

            # Poll until process is actually dead (up to 30s)
            for _ in range(60):
                if not psutil.pid_exists(pid):
                    break
                await asyncio.sleep(0.5)
            else:
                logger.warning(f"VM {vmid}: ACPI timeout. Escalating to SIGKILL.")
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGKILL)

        # Cleanup
        config = self.load_config(vmid)
        for nic in config["hardware"].get("nics", []):
            tap_name = f"tap{vmid}i{nic['id'][-1]}"
            try:
                await self.net_manager.delete_tap(tap_name)
            except Exception as e:
                logger.warning(f"VM {vmid}: Could not delete tap {tap_name}: {e}")

        config["vm"]["status"] = "stopped"
        self.save_config(vmid, config)
        logger.info(f"VM {vmid}: Fully stopped and resources cleaned.")

    async def reset(self, vmid: int) -> None:
        qmp = await self._get_qmp(vmid)
        try:
            await qmp.system_reset()
        finally:
            await qmp.disconnect()

    async def get_stats(self, vmid: int) -> dict:
        try:
            qmp = await self._get_qmp(vmid)
            status = await qmp.query_status()
            memory = await qmp.query_memory()
            await qmp.disconnect()
            return {
                "status":      status.get("status", "unknown"),
                "running":     status.get("running", False),
                "mem_total_mb": memory.get("base-memory", 0) // (1024*1024),
            }
        except Exception:
            return {"status": "stopped", "running": False}

    async def _get_qmp(self, vmid: int) -> QMPClient:
        qmp_sock = str(self.run_dir / f"qmp-{vmid}.sock")
        if not os.path.exists(qmp_sock):
            raise QMPError(f"QMP socket {qmp_sock} not found. Is the VM running?")
        qmp = QMPClient(qmp_sock)
        await qmp.connect()
        return qmp
