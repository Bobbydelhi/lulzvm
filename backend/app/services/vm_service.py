import logging
from typing import List, Optional
from datetime import datetime

from app.domain.models import VirtualMachine, VMStatus
from app.ports.hypervisor import IHypervisor
from app.ports.repository import IVMRepository

logger = logging.getLogger("lulzvm.services")

class VMService:
    def __init__(self, hypervisor: IHypervisor, repository: IVMRepository):
        self.hypervisor = hypervisor
        self.repository = repository

    def get_all(self) -> List[VirtualMachine]:
        vms = self.repository.get_all()
        # Update real-time status before returning
        for vm in vms:
            if self.hypervisor.is_running(vm.vmid):
                vm.status = VMStatus.RUNNING
            else:
                vm.status = VMStatus.STOPPED
        return vms

    def get_by_id(self, vmid: int) -> Optional[VirtualMachine]:
        vm = self.repository.get_by_id(vmid)
        if vm:
            if self.hypervisor.is_running(vm.vmid):
                vm.status = VMStatus.RUNNING
            else:
                vm.status = VMStatus.STOPPED
        return vm

    def create(self, vm: VirtualMachine) -> VirtualMachine:
        if self.repository.get_by_id(vm.vmid):
            raise ValueError(f"VM {vm.vmid} already exists.")
        
        vm.created = datetime.utcnow().isoformat()
        vm.status = VMStatus.STOPPED
        self.repository.save(vm)
        logger.info(f"Created VM {vm.vmid}")
        return vm

    async def start(self, vmid: int) -> None:
        vm = self.repository.get_by_id(vmid)
        if not vm:
            raise ValueError(f"VM {vmid} not found.")

        # Here we could also orchestrate TAP network creation, 
        # but for the MVP core we delegate to hypervisor.
        await self.hypervisor.start_vm(vm)
        
        vm.status = VMStatus.RUNNING
        self.repository.save(vm)

    async def stop(self, vmid: int, force: bool = False) -> None:
        vm = self.repository.get_by_id(vmid)
        if not vm:
            raise ValueError(f"VM {vmid} not found.")

        await self.hypervisor.stop_vm(vm, force=force)
        
        vm.status = VMStatus.STOPPED
        self.repository.save(vm)

    def delete(self, vmid: int) -> None:
        if self.hypervisor.is_running(vmid):
            raise ValueError(f"Cannot delete running VM {vmid}. Stop it first.")
            
        self.repository.delete(vmid)
        logger.info(f"Deleted VM {vmid}")
