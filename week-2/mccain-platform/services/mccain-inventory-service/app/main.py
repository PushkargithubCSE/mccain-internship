from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.routers import inventory, products, warehouses

app = FastAPI(
    title="McCain Inventory Service",
    description="Products, warehouses, and per-warehouse stock levels for the McCain distributed platform.",
    version="1.0.0",
)

app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(inventory.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "checks": {"postgres": True}}
    except Exception:
        return {"status": "degraded", "checks": {"postgres": False}}


@app.get("/")
async def root():
    return {"service": "mccain-inventory-service", "status": "running", "version": "1.0.0"}
