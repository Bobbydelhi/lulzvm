"""
CT Manager — gestiona el ciclo de vida de contenedores LXC.
"""
import asyncio
import logging
import os
import tomllib
import tomli_w
from pathlib import Path

from config import settings
from core.network import NetworkManager

logger = logging.getLogger("lulzvm.ct")

class CTManager:
    def __init__(self):
        self.config_dir = Path(settings.paths.config_dir) / "containers"
        self.lxc_path = "/var/lib/lxc"
        self.net_manager = NetworkManager()

    def load_config(self, ctid: int) -> dict:
        path = self.config_dir / f"{ctid}.toml"
        if not path.exists():
            raise FileNotFoundError(f"Container {ctid} not found")
        with open(path, "rb") as f:
            return tomllib.load(f)

    def save_config(self, ctid: int, config: dict) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        path = self.config_dir / f"{ctid}.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)

    def list_cts(self) -> list:
        cts = []
        for toml_file in self.config_dir.glob("*.toml"):
            try:
                with open(toml_file, "rb") as f:
                    cfg = tomllib.load(f)
                cts.append(cfg)
            except Exception as e:
                logger.warning(f"Cannot load {toml_file}: {e}")
        return cts

    async def _run_cmd(self, cmd: list) -> tuple:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()

    def _generate_lxc_config(self, config: dict) -> str:
        ctid = config["container"]["ctid"]
        res = config.get("resources", {})
        net = config.get("network", [])
        opt = config.get("options", {})
        
        cfg = [
            f"lxc.uts.name = {config['container']['name']}",
            f"lxc.rootfs.path = dir:{self.lxc_path}/{ctid}/rootfs",
            "lxc.include = /usr/share/lxc/config/common.conf",
        ]
        
        if not opt.get("privileged", False):
            cfg.append("lxc.include = /usr/share/lxc/config/userns.conf")
            cfg.append("lxc.idmap = u 0 100000 65536")
            cfg.append("lxc.idmap = g 0 100000 65536")

        if opt.get("nesting", False):
            cfg.append("lxc.include = /usr/share/lxc/config/nesting.conf")

        mem_bytes = res.get("memory_mb", 256) * 1024 * 1024
        swap_bytes = res.get("swap_mb", 256) * 1024 * 1024
        cfg.append(f"lxc.cgroup2.memory.max = {mem_bytes}")
        cfg.append(f"lxc.cgroup2.memory.swap.max = {swap_bytes}")
        
        cores = res.get("cores", 1)
        cfg.append(f"lxc.cgroup2.cpuset.cpus = 0-{cores-1}")
        
        cpu_limit = res.get("cpu_limit", 0)
        if cpu_limit > 0:
            quota = int((cpu_limit / 100) * 100000)
            cfg.append(f"lxc.cgroup2.cpu.max = {quota} 100000")

        for i, n in enumerate(net):
            cfg.append(f"lxc.net.{i}.type = veth")
            cfg.append(f"lxc.net.{i}.link = {n['bridge']}")
            cfg.append(f"lxc.net.{i}.flags = up")
            cfg.append(f"lxc.net.{i}.hwaddr = {n['mac']}")
            cfg.append(f"lxc.net.{i}.name = {n.get('id', 'eth0')}")
            if n.get("ip") != "dhcp":
                cfg.append(f"lxc.net.{i}.ipv4.address = {n['ip']}")
            if n.get("gw"):
                cfg.append(f"lxc.net.{i}.ipv4.gateway = {n['gw']}")

        return "\n".join(cfg)

    async def create_ct(self, ctid: int, name: str, template: str, 
                        memory_mb: int, cores: int, rootfs_storage: str,
                        rootfs_size_gb: int, bridge: str, ip: str, 
                        password: str, privileged: bool = False) -> dict:
        from datetime import datetime
        import random

        if (self.config_dir / f"{ctid}.toml").exists():
            raise ValueError(f"CT {ctid} already exists")

        try:
            dist, release, _ = template.split("-", 2)
        except ValueError:
            dist, release = "debian", "bookworm"

        cmd = [
            "lxc-create", "-n", str(ctid), "-t", "download", "--",
            "-d", dist, "-r", release, "-a", "amd64"
        ]
        
        logger.info(f"Creating CT {ctid}: {' '.join(cmd)}")
        code, stdout, stderr = await self._run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"lxc-create failed: {stderr}")

        mac = "AA:BB:CC:%02X:%02X:%02X" % (
            random.randint(0,255), random.randint(0,255), random.randint(0,255))
            
        config = {
            "container": {
                "ctid": ctid, "name": name, "status": "stopped",
                "created": datetime.utcnow().isoformat()
            },
            "os": {
                "template": template, "rootfs_storage": rootfs_storage,
                "rootfs_size_gb": rootfs_size_gb
            },
            "resources": {
                "memory_mb": memory_mb, "swap_mb": memory_mb,
                "cores": cores, "cpu_limit": 0
            },
            "network": [{
                "id": "eth0", "bridge": bridge, "mac": mac,
                "ip": ip, "gw": ""
            }],
            "options": {
                "onboot": False, "privileged": privileged, "nesting": False
            }
        }
        self.save_config(ctid, config)

        lxc_config_path = f"{self.lxc_path}/{ctid}/config"
        lxc_cfg_content = self._generate_lxc_config(config)
        with open(lxc_config_path, "w") as f:
            f.write(lxc_cfg_content)

        rootfs = f"{self.lxc_path}/{ctid}/rootfs"
        chpasswd_cmd = ["chroot", rootfs, "chpasswd"]
        proc = await asyncio.create_subprocess_exec(
            *chpasswd_cmd, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate(input=f"root:{password}\n".encode())
        if proc.returncode != 0:
            logger.warning(f"Failed to set root password for CT {ctid}: {stderr.decode()}")

        logger.info(f"CT {ctid} created successfully")
        return config

    async def start_ct(self, ctid: int) -> None:
        config = self.load_config(ctid)
        if self.get_status(ctid) == "running":
            raise RuntimeError(f"CT {ctid} is already running")

        lxc_config_path = f"{self.lxc_path}/{ctid}/config"
        with open(lxc_config_path, "w") as f:
            f.write(self._generate_lxc_config(config))

        cmd = ["lxc-start", "-n", str(ctid), "-d"]
        code, out, err = await self._run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"lxc-start failed: {err}")

        config["container"]["status"] = "running"
        self.save_config(ctid, config)
        logger.info(f"CT {ctid} started")

    async def stop_ct(self, ctid: int) -> None:
        config = self.load_config(ctid)
        if self.get_status(ctid) != "running":
            raise RuntimeError(f"CT {ctid} is not running")

        cmd = ["lxc-stop", "-n", str(ctid)]
        code, out, err = await self._run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"lxc-stop failed: {err}")

        config["container"]["status"] = "stopped"
        self.save_config(ctid, config)
        logger.info(f"CT {ctid} stopped")

    async def destroy_ct(self, ctid: int) -> None:
        status = self.get_status(ctid)
        if status == "running":
            raise RuntimeError(f"CT {ctid} is running. Stop it first.")

        cmd = ["lxc-destroy", "-n", str(ctid)]
        code, out, err = await self._run_cmd(cmd)
        if code != 0:
            raise RuntimeError(f"lxc-destroy failed: {err}")

        config_path = self.config_dir / f"{ctid}.toml"
        config_path.unlink(missing_ok=True)
        logger.info(f"CT {ctid} destroyed")

    def get_status(self, ctid: int) -> str:
        import subprocess
        try:
            r = subprocess.run(["lxc-info", "-n", str(ctid), "-s"], capture_output=True, text=True)
            if "RUNNING" in r.stdout:
                return "running"
            elif "STOPPED" in r.stdout:
                return "stopped"
            return "unknown"
        except Exception:
            return "unknown"

    async def get_stats(self, ctid: int) -> dict:
        status = self.get_status(ctid)
        stats = {"status": status, "running": status == "running"}
        if status == "running":
            try:
                mem_path = f"/sys/fs/cgroup/lxc.payload.{ctid}/memory.current"
                if os.path.exists(mem_path):
                    with open(mem_path, "r") as f:
                        mem_bytes = int(f.read().strip())
                        stats["mem_used_mb"] = mem_bytes // (1024 * 1024)
            except Exception as e:
                logger.debug(f"Failed to read cgroup stats for CT {ctid}: {e}")
        return stats
