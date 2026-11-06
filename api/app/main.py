"""Punto de entrada de la API de Brújula Viajes."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError, PyMongoError, ServerSelectionTimeoutError, WriteError

from .database import get_database
from .routers import clientes, hoteles, paquetes, reportes, reservas, tours, vuelos
from .setup_db import crear_esquema


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        crear_esquema(get_database())
    except ServerSelectionTimeoutError:
        print("ADVERTENCIA: no fue posible conectarse a MongoDB al iniciar")
    yield


app = FastAPI(title="Brújula Viajes API", version="1.0.0",
              description="Catálogo, reservas con control de inventario y reportes. FastAPI + PyMongo.",
              lifespan=lifespan)

for r in (clientes, vuelos, hoteles, tours, paquetes, reservas, reportes):
    app.include_router(r.router)


@app.exception_handler(DuplicateKeyError)
async def _duplicado(_: Request, exc: DuplicateKeyError):
    campo = ", ".join((exc.details or {}).get("keyValue", {}).keys()) or "clave única"
    return JSONResponse(status_code=409, content={"detail": f"Valor duplicado en {campo}"})


@app.exception_handler(WriteError)
async def _validacion(_: Request, exc: WriteError):
    if exc.code == 121:
        return JSONResponse(status_code=422, content={"detail": "El documento no cumple el validador de MongoDB",
                                                       "errInfo": str((exc.details or {}).get("errInfo"))[:800]})
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ServerSelectionTimeoutError)
async def _sin_bd(_: Request, exc: ServerSelectionTimeoutError):
    return JSONResponse(status_code=503, content={"detail": "No hay conexión con MongoDB"})


@app.exception_handler(PyMongoError)
async def _mongo(_: Request, exc: PyMongoError):
    return JSONResponse(status_code=500, content={"detail": f"Error de base de datos: {exc}"})


@app.get("/", tags=["Estado"])
def raiz():
    return {"servicio": "Brújula Viajes API", "documentacion": "/docs"}
