from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import VirtualMachine

class IVMRepository(ABC):
    @abstractmethod
    def get_by_id(self, vmid: int) -> Optional[VirtualMachine]:
        """Retrieves a VM by its ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[VirtualMachine]:
        """Retrieves all VMs."""
        pass

    @abstractmethod
    def save(self, vm: VirtualMachine) -> None:
        """Saves or updates a VM."""
        pass

    @abstractmethod
    def delete(self, vmid: int) -> None:
        """Deletes a VM configuration."""
        pass
