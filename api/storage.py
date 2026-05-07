"""
Router API para Storage — gestión de pools y discos.
"""
import logging
import shutil
import subprocess
import aiofiles
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, File, UploadFile
from typing import List
from pydantic import BaseModel

from core.storage import StorageManager

logger = logging.getLogger("lulzvm.api.storage")
router = APIRouter()
storage_manager = StorageManager()

class CreateDiskRequest(BaseModel):
    pool_id: str
    filename: str
    size_gb: int
    format: str = "qcow2"

@router.get("/", response_model=List[dict])
async def list_pools():
    """Lista pools de almacenamiento con espacio usado/libre"""
    pools = storage_manager.load_pools()
    result = []
    for pool in pools:
        info = pool.copy()
        try:
            if pool["type"] == "dir" and pool.get("enabled"):
                total, used, free = shutil.disk_usage(pool["path"])
                info["total_gb"] = round(total / (1024**3), 2)
                info["used_gb"] = round(used / (1024**3), 2)
                info["free_gb"] = round(free / (1024**3), 2)
            elif pool["type"] == "zfs" and pool.get("enabled"):
                r = subprocess.run(
                    ["zfs", "list", "-H", "-o", "used,available", pool["dataset"]],
                    capture_output=True, text=True
                )
                if r.returncode == 0:
                    used_str, avail_str = r.stdout.strip().split()
                    info["zfs_used"] = used_str
                    info["zfs_available"] = avail_str
        except Exception as e:
            logger.warning(f"Failed to get stats for pool {pool['id']}: {e}")
        result.append(info)
    return result

@router.post("/create-disk", status_code=201)
async def create_disk(req: CreateDiskRequest):
    """Crea un disco virtual usando StorageManager"""
    try:
        path = await storage_manager.create_disk(
            req.pool_id, req.filename, req.size_gb, req.format
        )
        return {"pool_id": req.pool_id, "filename": req.filename, "path": path, "status": "created"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{pool_id}/{filename}", status_code=204)
async def delete_disk(pool_id: str, filename: str):
    """Elimina un disco virtual de un pool"""
    try:
        await storage_manager.delete_disk(pool_id, filename)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-iso", status_code=201)
async def upload_iso(file: UploadFile = File(...)):
    """Sube un archivo .iso al almacenamiento local"""
    if not file.filename.endswith(".iso"):
        raise HTTPException(status_code=400, detail="Only .iso files are allowed")
    
    try:
        pool = storage_manager.get_pool("local")
        dest_path = Path(pool["path"]) / file.filename
        
        async with aiofiles.open(dest_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
        
        logger.info(f"ISO {file.filename} uploaded")
        return {"filename": file.filename, "status": "uploaded"}
    except Exception as e:
        logger.error(f"Error uploading ISO: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/isos", response_model=List[str])
async def list_isos():
    """Lista archivos .iso disponibles para montar en VMs"""
    try:
        pool = storage_manager.get_pool("local")
        path = Path(pool["path"])
        return [f.name for f in path.glob("*.iso")]
    except Exception as e:
        logger.warning(f"Could not list ISOs: {e}")
        return []
