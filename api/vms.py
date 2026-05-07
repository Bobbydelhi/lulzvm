"""
Router API para VMs — CRUD + lifecycle operations.
Includes robust error reporting and validation.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, WebSocket
from typing import List

from models import CreateVMRequest, UpdateVMRequest
from core.vm_manager import VMManager

logger = logging.getLogger("lulzvm.api.vms")
router = APIRouter()
vm_manager = VMManager()


@router.get("/", response_model=List[dict])
async def list_vms():
    vms = vm_manager.list_vms()
    result = []
    for cfg in vms:
        vmid = cfg["vm"]["vmid"]
        real_status = vm_manager.get_status(vmid)
        if cfg["vm"].get("status") != real_status:
            cfg["vm"]["status"] = real_status
            vm_manager.save_config(vmid, cfg)
        result.append({
            "vmid":      vmid,
            "name":      cfg["vm"]["name"],
            "status":    real_status,
            "memory_mb": cfg["hardware"]["memory_mb"],
            "cores":     cfg["hardware"]["cores"],
        })
    return result


@router.post("/", response_model=dict, status_code=201)
async def create_vm(req: CreateVMRequest):
    try:
        config = vm_manager.create_vm(
            vmid=req.vmid, name=req.name,
            memory_mb=req.memory_mb, cores=req.cores,
            cpu_type=req.cpu_type, machine=req.machine,
            bios=req.bios, cdrom=req.cdrom or "",
            disks=[d.model_dump() for d in req.disks],
            nics=[n.model_dump() for n in req.nics],
            onboot=req.onboot
        )
        return {"vmid": req.vmid, "status": "created", "config": config}
    except ValueError as e:
        logger.error(f"Validation error creating VM: {e}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error creating VM")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/{vmid}", response_model=dict)
async def get_vm(vmid: int):
    try:
        config = vm_manager.load_config(vmid)
        stats  = await vm_manager.get_stats(vmid)
        return {**config, "live_stats": stats}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"VM {vmid} not found")


@router.put("/{vmid}", response_model=dict)
async def update_vm(vmid: int, req: UpdateVMRequest):
    try:
        config = vm_manager.update_vm(vmid, **req.model_dump(exclude_unset=True))
        return {"vmid": vmid, "status": "updated", "config": config}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"VM {vmid} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vmid}", status_code=204)
async def delete_vm(vmid: int):
    try:
        vm_manager.delete_vm(vmid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"VM {vmid} not found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{vmid}/start")
async def start_vm(vmid: int):
    try:
        await vm_manager.start(vmid)
        return {"vmid": vmid, "action": "start", "status": "running"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unhandled error starting VM {vmid}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vmid}/stop")
async def stop_vm(vmid: int, force: bool = False):
    try:
        await vm_manager.stop(vmid, force=force)
        return {"vmid": vmid, "action": "stop", "status": "ok"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception(f"Unhandled error stopping VM {vmid}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vmid}/reset")
async def reset_vm(vmid: int):
    try:
        await vm_manager.reset(vmid)
        return {"vmid": vmid, "action": "reset", "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vmid}/status")
async def vm_status(vmid: int):
    stats = await vm_manager.get_stats(vmid)
    return {"vmid": vmid, **stats}


@router.websocket("/{vmid}/vnc")
async def vnc_proxy(websocket: WebSocket, vmid: int):
    """Proxy WebSocket a TCP para VNC, validando estado preventivamente."""
    await websocket.accept()
    
    try:
        status = vm_manager.get_status(vmid)
        if status != "running":
            await websocket.send_text("Error: VM is not running.")
            await websocket.close()
            return

        vnc_port = 5900 + vmid
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', vnc_port)
        except ConnectionRefusedError:
            logger.error(f"VNC Connection refused on port {vnc_port}")
            await websocket.send_text("Error: VNC service is not available on VM.")
            await websocket.close()
            return
            
        async def forward_to_vnc():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    writer.write(data)
                    await writer.drain()
            except:
                pass
            finally:
                writer.close()

        async def forward_to_websocket():
            try:
                while True:
                    data = await reader.read(8192)
                    if not data:
                        break
                    await websocket.send_bytes(data)
            except:
                pass
            finally:
                try:
                    await websocket.close()
                except:
                    pass

        await asyncio.gather(forward_to_vnc(), forward_to_websocket())
        
    except Exception as e:
        logger.error(f"VNC Proxy exception for VM {vmid}: {e}")
        try:
            await websocket.close()
        except:
            pass
