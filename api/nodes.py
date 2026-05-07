"""Info del nodo: CPU, RAM, discos, uptime, versión de QEMU/KVM"""
import subprocess
import psutil
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def node_info():
    cpu    = psutil.cpu_percent(interval=1)
    mem    = psutil.virtual_memory()
    disk   = psutil.disk_usage("/")
    uptime = int(psutil.boot_time())

    kvm_ok = subprocess.run(
        ["kvm-ok"], capture_output=True
    ).returncode == 0 if subprocess.run(
        ["which", "kvm-ok"], capture_output=True
    ).returncode == 0 else None

    qemu_ver = subprocess.run(
        ["qemu-system-x86_64", "--version"],
        capture_output=True, text=True
    ).stdout.split("\n")[0]

    return {
        "hostname":    subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip(),
        "cpu_usage":   cpu,
        "cpu_count":   psutil.cpu_count(),
        "mem_total_gb": round(mem.total / (1024**3), 2),
        "mem_used_gb":  round(mem.used  / (1024**3), 2),
        "mem_percent":  mem.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb":  round(disk.used  / (1024**3), 2),
        "uptime_epoch": uptime,
        "kvm_available": kvm_ok,
        "qemu_version": qemu_ver,
        "lulzvm_version": "1.0.0",
    }
