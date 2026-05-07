"""
Gestión de networking: Linux bridges y TAP devices.
"""
import asyncio
import logging
import tomllib
from pathlib import Path
from config import settings

logger = logging.getLogger("lulzvm.network")


async def _run(cmd: list) -> tuple:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


class NetworkManager:

    def __init__(self):
        self.config_path = Path(settings.paths.config_dir) / "network.toml"

    def load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                return tomllib.load(f)
        return {"bridges": []}

    def save_config(self, config: dict) -> None:
        import tomli_w
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "wb") as f:
            tomli_w.dump(config, f)

    async def setup_bridges(self) -> None:
        """Crea todos los bridges definidos en network.toml al arrancar lulzVM"""
        config = self.load_config()
        for bridge in config.get("bridges", []):
            if bridge.get("autostart"):
                await self.create_bridge(
                    name=bridge["name"],
                    address=bridge.get("address"),
                    interfaces=bridge.get("interfaces", [])
                )

    async def create_bridge(self, name: str, address: str = None, interfaces: list = None) -> None:
        code, _, err = await _run(["ip", "link", "show", name])
        if code == 0:
            logger.debug(f"Bridge {name} already exists")
        else:
            logger.info(f"Creating bridge {name}")
            await _run(["ip", "link", "add", "name", name, "type", "bridge"])
            await _run(["ip", "link", "set", name, "up"])

        if interfaces:
            for iface in interfaces:
                await _run(["ip", "link", "set", iface, "master", name])
                await _run(["ip", "link", "set", iface, "up"])

        if address:
            # Eliminar la ip del device si ya la tiene o configurarla (esto asume que no falla si ya está)
            await _run(["ip", "addr", "add", address, "dev", name])

        # Permitir forwarding
        await _run(["sysctl", "-w", f"net.ipv4.conf.{name}.forwarding=1"])

    async def delete_bridge(self, name: str) -> None:
        await _run(["ip", "link", "set", name, "down"])
        await _run(["ip", "link", "del", name])

    async def create_tap(self, tap_name: str, bridge: str) -> None:
        """Crea un TAP device y lo conecta al bridge"""
        # Eliminar si existe (limpieza de crash anterior)
        await _run(["ip", "link", "del", tap_name])

        code, _, err = await _run([
            "ip", "tuntap", "add", "dev", tap_name, "mode", "tap"
        ])
        if code != 0:
            raise RuntimeError(f"Cannot create tap {tap_name}: {err}")

        await _run(["ip", "link", "set", tap_name, "master", bridge])
        await _run(["ip", "link", "set", tap_name, "up"])
        # Activar promiscuous mode en el TAP para que el bridge reciba todo
        await _run(["ip", "link", "set", tap_name, "promisc", "on"])
        logger.debug(f"TAP {tap_name} created and attached to {bridge}")

    async def delete_tap(self, tap_name: str) -> None:
        code, _, _ = await _run(["ip", "link", "show", tap_name])
        if code == 0:
            await _run(["ip", "link", "del", tap_name])
            logger.debug(f"TAP {tap_name} deleted")
