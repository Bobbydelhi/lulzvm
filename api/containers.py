"""
Router API para CTs — CRUD + lifecycle operations.
"""
import logging
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from models import CreateCTRequest
from core.ct_manager import CTManager

logger = logging.getLogger("lulzvm.api.containers")
router = APIRouter()
ct_manager = CTManager()

@router.get("/", response_model=List[dict])
async def list_cts():
    """Lista todos los contenedores con su configuración y estado actual"""
    cts = ct_manager.list_cts()
    result = []
    for cfg in cts:
        ctid = cfg["container"]["ctid"]
        status = ct_manager.get_status(ctid)
        result.append({
            "ctid":      ctid,
            "name":      cfg["container"]["name"],
            "status":    status,
            "memory_mb": cfg["resources"]["memory_mb"],
            "cores":     cfg["resources"]["cores"],
            "ip":        cfg["network"][0]["ip"] if cfg.get("network") else ""
        })
    return result

@router.post("/", response_model=dict, status_code=201)
async def create_ct(req: CreateCTRequest):
    """Creates a new LXC container."""
    try:
        config = await ct_manager.create_ct(
            ctid=req.ctid, name=req.name, template=req.template,
            memory_mb=req.memory_mb, cores=req.cores,
            rootfs_storage=req.rootfs_storage, rootfs_size_gb=req.rootfs_size_gb,
            bridge=req.bridge, ip=req.ip, password=req.password,
            privileged=req.privileged
        )
        return {"ctid": req.ctid, "status": "created", "config": config}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ctid}", response_model=dict)
async def get_ct(ctid: int):
    """Obtiene la configuración y estadísticas de un contenedor"""
    try:
        config = ct_manager.load_config(ctid)
        stats = await ct_manager.get_stats(ctid)
        return {**config, "live_stats": stats}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CT {ctid} not found")

@router.delete("/{ctid}", status_code=204)
async def delete_ct(ctid: int):
    """Elimina un contenedor LXC"""
    try:
        await ct_manager.destroy_ct(ctid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CT {ctid} not found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{ctid}/start")
async def start_ct(ctid: int, bg: BackgroundTasks):
    """Arranca un contenedor LXC"""
    try:
        bg.add_task(ct_manager.start_ct, ctid)
        return {"ctid": ctid, "action": "start", "status": "queued"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CT {ctid} not found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/{ctid}/stop")
async def stop_ct(ctid: int):
    """Detiene un contenedor LXC"""
    try:
        await ct_manager.stop_ct(ctid)
        return {"ctid": ctid, "action": "stop", "status": "ok"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CT {ctid} not found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/{ctid}/restart")
async def restart_ct(ctid: int, bg: BackgroundTasks):
    """Reinicia un contenedor LXC"""
    try:
        async def restart():
            await ct_manager.stop_ct(ctid)
            await asyncio.sleep(2)
            await ct_manager.start_ct(ctid)
        bg.add_task(restart)
        return {"ctid": ctid, "action": "restart", "status": "queued"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CT {ctid} not found")
