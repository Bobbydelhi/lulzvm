from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class VMStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class DiskConfig(BaseModel):
    id: str = "scsi0"
    bus: str = "virtio"
    storage: str = "local"
    file: str
    size_gb: int = Field(default=10, ge=1, le=32768)
    cache: str = "none"
    aio: str = "io_uring"


class NICConfig(BaseModel):
    id: str = "net0"
    model: str = "virtio"
    bridge: str = "lulzbr0"
    mac: str = ""
    vlan: int = 0


class BootConfig(BaseModel):
    order: List[str] = ["scsi0"]
    cdrom: Optional[str] = None


class VMHardware(BaseModel):
    memory_mb: int = 512
    cores: int = 1
    sockets: int = 1
    cpu_type: str = "host"
    machine: str = "q35"
    bios: str = "seabios"
    disks: List[DiskConfig] = []
    nics: List[NICConfig] = []


class VMOptions(BaseModel):
    onboot: bool = False
    agent: bool = False
    tablet: bool = True
    vnc_port: Optional[int] = None


class VirtualMachine(BaseModel):
    vmid: int = Field(ge=100, le=999999999)
    name: str = Field(min_length=1, max_length=64)
    status: VMStatus = VMStatus.STOPPED
    created: Optional[str] = None
    hardware: VMHardware = Field(default_factory=VMHardware)
    boot: BootConfig = Field(default_factory=BootConfig)
    options: VMOptions = Field(default_factory=VMOptions)

    def is_running(self) -> bool:
        return self.status == VMStatus.RUNNING
