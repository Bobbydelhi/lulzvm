import asyncio
import logging
import os
import signal
from pathlib import Path

from app.domain.models import VirtualMachine, VMStatus
from app.ports.hypervisor import IHypervisor
# Assuming QMPClient is moved to core or infrastructure later, for now import from legacy if needed,
# but we will rewrite it or port it. Let's assume we port it to backend/app/infrastructure/qemu/qmp_client.py
from app.infrastructure.qemu.qmp_client import QMPClient, QMPError


logger = logging.getLogger("lulzvm.qemu")

class QemuAdapter(IHypervisor):
    def __init__(self, run_dir: str = "/run/lulzvm", log_dir: str = "/var/log/lulzvm/vms"):
        self.run_dir = Path(run_dir)
        self.log_dir = Path(log_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_pid_file(self, vmid: int) -> Path:
        return self.run_dir / f"{vmid}.pid"

    def _get_qmp_socket(self, vmid: int) -> Path:
        return self.run_dir / f"qmp-{vmid}.sock"
        
    def _get_serial_socket(self, vmid: int) -> Path:
        return self.run_dir / f"serial-{vmid}.sock"

    def is_running(self, vmid: int) -> bool:
        pid_file = self._get_pid_file(vmid)
        if not pid_file.exists():
            return False
        
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            # Check if process is actually alive
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, OSError):
            # Stale PID file
            pid_file.unlink(missing_ok=True)
            return False

    def _build_cmd(self, vm: VirtualMachine) -> list:
        # Simplistic builder based on the old one, but isolated.
        hw = vm.hardware
        opt = vm.options
        vmid = vm.vmid

        qmp_sock = str(self._get_qmp_socket(vmid))
        serial_sock = str(self._get_serial_socket(vmid))
        pid_file = str(self._get_pid_file(vmid))
        log_file = str(self.log_dir / f"{vmid}.log")

        accel = "kvm" if os.path.exists("/dev/kvm") else "tcg"
        cpu_type = hw.cpu_type
        if accel == "tcg" and cpu_type == "host":
            cpu_type = "max"

        cmd = [
            "qemu-system-x86_64",
            "-nodefaults", "-no-user-config",
            "-pidfile", pid_file,
            "-chardev", f"socket,id=charmonitor,path={qmp_sock},server=on,wait=off",
            "-mon", "chardev=charmonitor,id=monitor,mode=control",
            "-machine", f"{hw.machine},accel={accel}",
            "-cpu", cpu_type,
            "-smp", f"{hw.cores},sockets={hw.sockets},cores={hw.cores},maxcpus={hw.cores}",
            "-m", str(hw.memory_mb),
            "-D", log_file,
            "-chardev", f"socket,id=charserial0,path={serial_sock},server=on,wait=off",
            "-device", "isa-serial,chardev=charserial0,id=serial0",
            "-vga", "std",
            "-k", "en-us"
        ]
        
        if opt.tablet:
            cmd += ["-device", "usb-ehci,id=ehci", "-device", "usb-tablet,bus=ehci.0"]

        if opt.vnc_port:
            cmd += ["-vnc", f":{opt.vnc_port - 5900}"]
            
        cmd += ["-daemonize"]
        return cmd

    async def start_vm(self, vm: VirtualMachine) -> None:
        if self.is_running(vm.vmid):
            raise RuntimeError(f"VM {vm.vmid} is already running.")

        cmd = self._build_cmd(vm)
        logger.info(f"Starting VM {vm.vmid}")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"QEMU failed to start: {stderr.decode().strip()}")
            
        # Wait for QMP socket
        qmp_sock = self._get_qmp_socket(vm.vmid)
        for _ in range(30):
            if qmp_sock.exists():
                break
            await asyncio.sleep(0.5)
        else:
            # Cleanup if hung
            if self.is_running(vm.vmid):
                with open(self._get_pid_file(vm.vmid), "r") as f:
                    os.kill(int(f.read().strip()), signal.SIGKILL)
            raise RuntimeError("QMP socket never appeared.")

    async def stop_vm(self, vm: VirtualMachine, force: bool = False) -> None:
        if not self.is_running(vm.vmid):
            return
            
        pid_file = self._get_pid_file(vm.vmid)
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        if force:
            os.kill(pid, signal.SIGKILL)
            logger.info(f"Force killed VM {vm.vmid}")
        else:
            try:
                qmp_sock = str(self._get_qmp_socket(vm.vmid))
                qmp = QMPClient(qmp_sock)
                await qmp.connect()
                await qmp.system_powerdown()
                await qmp.disconnect()
            except Exception as e:
                logger.error(f"Failed graceful shutdown via QMP for {vm.vmid}: {e}")
                os.kill(pid, signal.SIGKILL)
                return

            # Wait for exit
            for _ in range(60):
                if not self.is_running(vm.vmid):
                    break
                await asyncio.sleep(0.5)
            else:
                logger.warning(f"Graceful shutdown timed out for VM {vm.vmid}, killing.")
                if self.is_running(vm.vmid):
                    os.kill(pid, signal.SIGKILL)

    async def get_vm_stats(self, vm: VirtualMachine) -> dict:
        if not self.is_running(vm.vmid):
            return {"status": "stopped"}
        try:
            qmp_sock = str(self._get_qmp_socket(vm.vmid))
            qmp = QMPClient(qmp_sock)
            await qmp.connect()
            status = await qmp.query_status()
            memory = await qmp.query_memory()
            await qmp.disconnect()
            return {
                "status": status.get("status", "unknown"),
                "running": status.get("running", False),
                "mem_total_mb": memory.get("base-memory", 0) // (1024 * 1024)
            }
        except Exception:
            return {"status": "error"}
