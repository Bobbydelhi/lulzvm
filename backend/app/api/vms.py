from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.domain.models import VirtualMachine
from app.services.vm_service import VMService
from app.infrastructure.persistence.toml_repository import TomlVMRepository
from app.infrastructure.qemu.qemu_adapter import QemuAdapter

router = APIRouter()

# Dependency Injection for the Service
def get_vm_service() -> VMService:
    repo = TomlVMRepository()
    hypervisor = QemuAdapter()
    return VMService(hypervisor=hypervisor, repository=repo)


@router.get("/", response_model=List[VirtualMachine])
def list_vms(service: VMService = Depends(get_vm_service)):
    return service.get_all()


@router.post("/", response_model=VirtualMachine, status_code=status.HTTP_201_CREATED)
def create_vm(vm: VirtualMachine, service: VMService = Depends(get_vm_service)):
    try:
        return service.create(vm)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{vmid}", response_model=VirtualMachine)
def get_vm(vmid: int, service: VMService = Depends(get_vm_service)):
    vm = service.get_by_id(vmid)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm


@router.post("/{vmid}/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_vm(vmid: int, service: VMService = Depends(get_vm_service)):
    try:
        await service.start(vmid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vmid}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_vm(vmid: int, force: bool = False, service: VMService = Depends(get_vm_service)):
    try:
        await service.stop(vmid, force=force)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vmid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vm(vmid: int, service: VMService = Depends(get_vm_service)):
    try:
        service.delete(vmid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
