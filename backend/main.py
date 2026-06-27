import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import vms

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lulzvm")

app = FastAPI(
    title="lulzVM API (Refactored)",
    version="2.0.0",
    description="Open source hypervisor platform - Clean Architecture MVP",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vms.router, prefix="/api/vms", tags=["vms"])

# TODO: Add Network, Storage, Containers, Nodes routers using the new architecture.

@app.on_event("startup")
async def startup_event():
    logger.info("lulzVM Refactored MVP is starting...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("lulzVM Refactored MVP is shutting down...")
