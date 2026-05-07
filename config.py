"""
Carga y valida la configuración de lulzVM desde archivos TOML.
Usa pydantic para validación estricta.
"""
import tomllib
from pathlib import Path
from pydantic import BaseModel
from typing import Optional


class DaemonConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8006
    workers: int = 4
    debug: bool = False
    log_level: str = "INFO"


class PathsConfig(BaseModel):
    config_dir: str  = "/etc/lulzvm"
    run_dir: str     = "/run/lulzvm"
    log_dir: str     = "/var/log/lulzvm"
    state_file: str  = "/var/lib/lulzvm/state.json"



class DefaultsConfig(BaseModel):
    vm_memory_mb: int   = 512
    vm_cores: int       = 1
    vm_storage_gb: int  = 10
    ct_memory_mb: int   = 256
    ct_cores: int       = 1
    default_bridge: str = "lulzbr0"


class LulzVMSettings(BaseModel):
    daemon: DaemonConfig     = DaemonConfig()
    paths: PathsConfig       = PathsConfig()
    defaults: DefaultsConfig = DefaultsConfig()

    @classmethod
    def load(cls, path: str = "/etc/lulzvm/lulzvm.toml") -> "LulzVMSettings":
        config_path = Path(path)
        if config_path.exists():
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            return cls(**data)
        return cls()


settings = LulzVMSettings.load()
