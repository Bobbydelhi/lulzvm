import psutil
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from core.network import NetworkManager

router = APIRouter()
net_manager = NetworkManager()

class BridgeConfig(BaseModel):
    name: str
    address: Optional[str] = None
    autostart: bool = True
    interfaces: List[str] = []

class NetworkConfig(BaseModel):
    bridges: List[BridgeConfig]

@router.get("/interfaces")
async def list_interfaces():
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    result = []
    for name, stat in stats.items():
        if name == "lo" or name.startswith("veth") or name.startswith("tap") or name.startswith("lulzbr") or name.startswith("vmbr"):
            continue
        ip = ""
        if name in addrs:
            for a in addrs[name]:
                if a.family.name == "AF_INET":
                    ip = a.address
        result.append({
            "name": name,
            "isup": stat.isup,
            "speed": stat.speed,
            "ip": ip
        })
    return result

@router.get("/bridges")
async def list_bridges():
    return net_manager.load_config().get("bridges", [])

@router.post("/bridges")
async def save_bridges(config: NetworkConfig):
    net_manager.save_config(config.model_dump())
    return {"status": "ok"}

@router.post("/apply")
async def apply_network():
    await net_manager.setup_bridges()
    return {"status": "ok"}
