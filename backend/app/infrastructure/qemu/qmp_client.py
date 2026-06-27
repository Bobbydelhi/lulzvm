"""
QMP (QEMU Machine Protocol) async client.
Comunica con QEMU via socket Unix usando el protocolo JSON de QMP.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger("lulzvm.qmp")


class QMPError(Exception):
    pass


class QMPClient:
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self._reader: Optional[asyncio.StreamReader]  = None
        self._writer: Optional[asyncio.StreamWriter]  = None
        self._event_handlers: Dict[str, Callable]     = {}
        self._connected = False

    async def connect(self, timeout: float = 10.0) -> None:
        """Conecta al socket QMP y realiza el handshake inicial"""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.socket_path),
                timeout=timeout
            )
        except (FileNotFoundError, ConnectionRefusedError) as e:
            raise QMPError(f"Cannot connect to QMP socket {self.socket_path}: {e}")

        # Leer greeting: {"QMP": {"version": {...}, "capabilities": [...]}}
        greeting = await self._recv_json()
        logger.debug(f"QMP greeting: {greeting}")

        # Negociar capabilities
        await self._send_json({"execute": "qmp_capabilities"})
        response = await self._recv_json()
        if "error" in response:
            raise QMPError(f"QMP capabilities negotiation failed: {response['error']}")

        self._connected = True
        logger.debug(f"QMP connected: {self.socket_path}")

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._connected = False

    async def execute(self, command: str, arguments: dict = None) -> Any:
        """Ejecuta un comando QMP y retorna el campo 'return'"""
        if not self._connected:
            raise QMPError("Not connected to QMP socket")

        msg = {"execute": command}
        if arguments:
            msg["arguments"] = arguments

        await self._send_json(msg)

        # QMP puede enviar eventos asíncronos antes de la respuesta del comando
        while True:
            response = await self._recv_json()
            if "return" in response:
                return response["return"]
            elif "error" in response:
                raise QMPError(f"QMP command error: {response['error']['desc']}")
            elif "event" in response:
                await self._dispatch_event(response)
            else:
                logger.warning(f"Unexpected QMP response: {response}")

    async def _send_json(self, data: dict) -> None:
        payload = json.dumps(data) + "\n"
        self._writer.write(payload.encode())
        await self._writer.drain()

    async def _recv_json(self) -> dict:
        line = await asyncio.wait_for(self._reader.readline(), timeout=30.0)
        if not line:
            raise QMPError("QMP connection closed unexpectedly")
        return json.loads(line.decode().strip())

    async def _dispatch_event(self, event: dict) -> None:
        event_name = event.get("event", "")
        handler = self._event_handlers.get(event_name)
        if handler:
            await handler(event)
        else:
            logger.debug(f"QMP event (unhandled): {event_name}")

    def on_event(self, event_name: str):
        def decorator(fn):
            self._event_handlers[event_name] = fn
            return fn
        return decorator

    # ── Comandos de alto nivel ──────────────────────────────────────────────

    async def query_status(self) -> dict:
        return await self.execute("query-status")

    async def query_memory(self) -> dict:
        return await self.execute("query-memory-size-summary")

    async def query_cpus(self) -> list:
        return await self.execute("query-cpus-fast")

    async def query_block(self) -> list:
        """Obtiene info de dispositivos de bloque (útil para backup incremental)"""
        return await self.execute("query-block")

    async def system_powerdown(self) -> None:
        """ACPI shutdown (graceful)"""
        await self.execute("system_powerdown")

    async def system_reset(self) -> None:
        await self.execute("system_reset")

    async def stop(self) -> None:
        """Pausa la VM (freeze vCPUs)"""
        await self.execute("stop")

    async def cont(self) -> None:
        """Reanuda la VM pausada"""
        await self.execute("cont")

    async def savevm(self, name: str) -> None:
        """Crea un snapshot interno (requiere disco qcow2)"""
        await self.execute("human-monitor-command",
                           {"command-line": f"savevm {name}"})

    async def loadvm(self, name: str) -> None:
        await self.execute("human-monitor-command",
                           {"command-line": f"loadvm {name}"})

    async def migrate(self, target_uri: str, live: bool = True) -> None:
        """
        Live migration a otro host.
        target_uri ejemplo: 'tcp:192.168.1.11:4444'
        """
        if live:
            await self.execute("migrate-set-capabilities", {
                "capabilities": [
                    {"capability": "xbzrle",        "state": True},
                    {"capability": "auto-converge",  "state": True},
                ]
            })
        await self.execute("migrate", {"uri": target_uri})

    async def device_add(self, driver: str, device_id: str, **kwargs) -> None:
        args = {"driver": driver, "id": device_id, **kwargs}
        await self.execute("device_add", args)

    async def device_del(self, device_id: str) -> None:
        await self.execute("device_del", {"id": device_id})
