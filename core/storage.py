"""
Storage plugins para lulzVM.
Soporta: directorios locales (raw/qcow2) y ZFS zvols.
"""
import asyncio
import logging
import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from config import settings

logger = logging.getLogger("lulzvm.storage")


class StorageManager:

    def __init__(self):
        self.config_path = Path(settings.paths.config_dir) / "storage.toml"
        self._pools: dict = {}

    def load_pools(self) -> list:
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "pools": [
                    {
                        "id": "local",
                        "name": "Local Directory",
                        "type": "dir",
                        "path": "/var/lib/lulzvm/images",
                        "enabled": True
                    }
                ]
            }
            import tomli_w
            with open(self.config_path, "wb") as f:
                tomli_w.dump(default_config, f)
                
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("pools", [])
        return []

    async def initialize_pools(self) -> None:
        for pool in self.load_pools():
            if not pool.get("enabled"):
                continue
            if pool["type"] == "dir":
                Path(pool["path"]).mkdir(parents=True, exist_ok=True)
                logger.info(f"Storage pool '{pool['id']}' (dir) ready: {pool['path']}")
            elif pool["type"] == "zfs":
                # Verificar que el dataset ZFS existe
                r = subprocess.run(
                    ["zfs", "list", pool["dataset"]],
                    capture_output=True
                )
                if r.returncode != 0:
                    subprocess.run(
                        ["zfs", "create", "-o", "compression=lz4",
                         "-o", "atime=off", pool["dataset"]], check=True
                    )
                    logger.info(f"ZFS dataset {pool['dataset']} created")
            self._pools[pool["id"]] = pool

    def get_pool(self, pool_id: str) -> dict:
        pools = self.load_pools()
        for p in pools:
            if p["id"] == pool_id:
                return p
        raise KeyError(f"Storage pool '{pool_id}' not found")

    def get_disk_path(self, pool_id: str, filename: str) -> str:
        pool = self.get_pool(pool_id)
        if pool["type"] == "dir":
            return str(Path(pool["path"]) / filename)
        elif pool["type"] == "zfs":
            zvol_name = filename  # e.g. "vm-100-disk-0"
            return f"/dev/zvol/{pool['dataset']}/{zvol_name}"
        raise ValueError(f"Unknown pool type: {pool['type']}")

    async def create_disk(self, pool_id: str, filename: str,
                          size_gb: int, fmt: str = "qcow2") -> str:
        """Crea un disco virtual en el pool especificado"""
        pool = self.get_pool(pool_id)

        if pool["type"] == "dir":
            path = Path(pool["path"]) / filename
            if fmt == "qcow2":
                cmd = ["qemu-img", "create", "-f", "qcow2",
                       "-o", "cluster_size=2M",
                       str(path), f"{size_gb}G"]
            else:
                cmd = ["qemu-img", "create", "-f", "raw",
                       str(path), f"{size_gb}G"]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"qemu-img create failed: {stderr.decode()}")
            logger.info(f"Disk {path} ({size_gb}G {fmt}) created")
            return str(path)

        elif pool["type"] == "zfs":
            zvol_path = f"{pool['dataset']}/{filename}"
            proc = await asyncio.create_subprocess_exec(
                "zfs", "create",
                "-V", f"{size_gb}G",
                "-o", "volblocksize=8k",
                "-o", "compression=lz4",
                zvol_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"zfs create failed: {stderr.decode()}")
            logger.info(f"ZFS zvol {zvol_path} ({size_gb}G) created")
            return f"/dev/zvol/{zvol_path}"

        raise ValueError(f"Unsupported pool type: {pool['type']}")

    async def delete_disk(self, pool_id: str, filename: str) -> None:
        pool = self.get_pool(pool_id)
        if pool["type"] == "dir":
            path = Path(pool["path"]) / filename
            path.unlink(missing_ok=True)
        elif pool["type"] == "zfs":
            zvol_path = f"{pool['dataset']}/{filename}"
            subprocess.run(["zfs", "destroy", zvol_path], check=True)

    async def resize_disk(self, pool_id: str, filename: str, new_size_gb: int) -> None:
        pool = self.get_pool(pool_id)
        if pool["type"] == "dir":
            path = str(Path(pool["path"]) / filename)
            subprocess.run(
                ["qemu-img", "resize", path, f"{new_size_gb}G"], check=True
            )
