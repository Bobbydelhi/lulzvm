"""Pydantic models para validación de requests/responses de la API"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from enum import Enum


class VMStatus(str, Enum):
    stopped  = "stopped"
    running  = "running"
    paused   = "paused"
    error    = "error"


class DiskConfig(BaseModel):
    id: str                = "scsi0"
    bus: str               = "virtio"
    storage: str           = "local"
    file: str
    size_gb: int           = Field(default=10, ge=1, le=32768)
    cache: str             = "none"
    aio: str               = "io_uring"


class NICConfig(BaseModel):
    id: str                = "net0"
    model: str             = "virtio"
    bridge: str            = "lulzbr0"
    mac: str               = ""
    vlan: int              = 0

    @field_validator("mac", mode="before")
    @classmethod
    def generate_mac(cls, v):
        if not v:
            import random
            return "AA:BB:CC:%02X:%02X:%02X" % (
                random.randint(0,255), random.randint(0,255), random.randint(0,255))
        return v


class CreateVMRequest(BaseModel):
    vmid: int              = Field(ge=100, le=999999999)
    name: str              = Field(min_length=1, max_length=64)
    memory_mb: int         = Field(default=512, ge=32, le=4194304)
    cores: int             = Field(default=1, ge=1, le=512)
    cpu_type: str          = "host"
    machine: str           = "q35"
    bios: str              = "seabios"
    disks: List[DiskConfig] = []
    nics: List[NICConfig]   = []
    cdrom: Optional[str]   = None
    onboot: bool           = False


class UpdateVMRequest(BaseModel):
    name: Optional[str]        = None
    memory_mb: Optional[int]   = None
    cores: Optional[int]       = None
    cdrom: Optional[str]       = None
    onboot: Optional[bool]     = None


class VMResponse(BaseModel):
    vmid: int
    name: str
    status: VMStatus
    memory_mb: int
    cores: int
    uptime: Optional[int]   = None
    cpu_usage: Optional[float] = None
    mem_usage_mb: Optional[int] = None


class CreateCTRequest(BaseModel):
    ctid: int              = Field(ge=100, le=999999999)
    name: str
    template: str          = "debian-12-standard"
    rootfs_storage: str    = "local"
    rootfs_size_gb: int    = Field(default=8, ge=1)
    memory_mb: int         = Field(default=256, ge=32)
    swap_mb: int           = 256
    cores: int             = Field(default=1, ge=1)
    bridge: str            = "lulzbr0"
    ip: str                = "dhcp"
    privileged: bool       = False
    password: str          = Field(min_length=8)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
