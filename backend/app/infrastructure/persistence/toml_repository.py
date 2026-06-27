import os
from pathlib import Path
from typing import List, Optional
import tomllib
import tomli_w

from app.domain.models import VirtualMachine, VMHardware, BootConfig, VMOptions, VMStatus
from app.ports.repository import IVMRepository


class TomlVMRepository(IVMRepository):
    def __init__(self, config_dir: str = "/etc/lulzvm/vms"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _to_domain(self, data: dict) -> VirtualMachine:
        # Map flat dict structure from legacy to domain model
        vm_data = data.get("vm", {})
        hw_data = data.get("hardware", {})
        boot_data = data.get("boot", {})
        opt_data = data.get("options", {})

        return VirtualMachine(
            vmid=vm_data.get("vmid"),
            name=vm_data.get("name"),
            status=VMStatus(vm_data.get("status", "stopped")),
            created=vm_data.get("created"),
            hardware=VMHardware(**hw_data),
            boot=BootConfig(**boot_data),
            options=VMOptions(**opt_data)
        )

    def _to_dict(self, vm: VirtualMachine) -> dict:
        # Convert domain model back to dict for TOML
        return {
            "vm": {
                "vmid": vm.vmid,
                "name": vm.name,
                "status": vm.status.value,
                "created": vm.created
            },
            "hardware": vm.hardware.model_dump(),
            "boot": vm.boot.model_dump(),
            "options": vm.options.model_dump()
        }

    def get_by_id(self, vmid: int) -> Optional[VirtualMachine]:
        path = self.config_dir / f"{vmid}.toml"
        if not path.exists():
            return None
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return self._to_domain(data)

    def get_all(self) -> List[VirtualMachine]:
        vms = []
        for toml_file in self.config_dir.glob("*.toml"):
            try:
                with open(toml_file, "rb") as f:
                    data = tomllib.load(f)
                vms.append(self._to_domain(data))
            except Exception:
                pass
        return vms

    def save(self, vm: VirtualMachine) -> None:
        path = self.config_dir / f"{vm.vmid}.toml"
        data = self._to_dict(vm)
        with open(path, "wb") as f:
            tomli_w.dump(data, f)

    def delete(self, vmid: int) -> None:
        path = self.config_dir / f"{vmid}.toml"
        if path.exists():
            path.unlink()
