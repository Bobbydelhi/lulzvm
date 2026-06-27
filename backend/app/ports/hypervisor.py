from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import VirtualMachine

class IHypervisor(ABC):
    @abstractmethod
    async def start_vm(self, vm: VirtualMachine) -> None:
        """Starts the virtual machine."""
        pass

    @abstractmethod
    async def stop_vm(self, vm: VirtualMachine, force: bool = False) -> None:
        """Stops the virtual machine gracefully or forcefully."""
        pass

    @abstractmethod
    async def get_vm_stats(self, vm: VirtualMachine) -> dict:
        """Returns statistics for the virtual machine (memory usage, CPU, etc)."""
        pass
    
    @abstractmethod
    def is_running(self, vmid: int) -> bool:
        """Returns true if the VM process is currently running on the host."""
        pass
