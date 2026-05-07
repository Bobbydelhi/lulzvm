"""
lulzVM — Main entrypoint
FastAPI application, mounts all routers and serves static UI
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.network import NetworkManager
from core.storage import StorageManager
from api import vms, containers, storage, nodes, network

STATIC_DIR = Path("./static")

logging.basicConfig(
    level=getattr(logging, settings.daemon.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(f"{settings.paths.log_dir}/daemon.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("lulzvm")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks"""
    logger.info("lulzVM starting up...")
    import os
    for d in [settings.paths.run_dir, settings.paths.log_dir,
              f"{settings.paths.log_dir}/vms", "/var/lib/lulzvm/images"]:
        os.makedirs(d, exist_ok=True)



    # Inicializar bridges de red
    net = NetworkManager()
    await net.setup_bridges()

    # Inicializar storage pools
    store = StorageManager()
    await store.initialize_pools()

    logger.info(f"lulzVM ready on {settings.daemon.host}:{settings.daemon.port}")
    yield
    logger.info("lulzVM shutting down...")


app = FastAPI(
    title="lulzVM API",
    version="1.0.0",
    description="Open source hypervisor platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(nodes.router,         prefix="/api/nodes",      tags=["nodes"])
app.include_router(network.router,       prefix="/api/network",    tags=["network"])
app.include_router(vms.router,           prefix="/api/vms",        tags=["vms"])
app.include_router(containers.router,    prefix="/api/containers", tags=["containers"])
app.include_router(storage.router,       prefix="/api/storage",    tags=["storage"])


# Servir archivos estáticos con cabeceras no-cache para evitar problemas de caché del navegador
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_static(full_path: str, request: Request):
    file_path = STATIC_DIR / full_path

    if not file_path.exists() or file_path.is_dir():
        file_path = STATIC_DIR / "index.html"

    suffix = file_path.suffix.lower()
    mime_types = {
        ".html": "text/html; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
        ".json": "application/json",
        ".ico":  "image/x-icon",
        ".png":  "image/png",
        ".svg":  "image/svg+xml",
    }
    content_type = mime_types.get(suffix, "application/octet-stream")

    no_cache_headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return FileResponse(
        path=file_path,
        media_type=content_type,
        headers=no_cache_headers,
    )
