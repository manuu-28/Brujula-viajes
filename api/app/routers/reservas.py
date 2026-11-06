from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from ..database import get_db
from ..schemas import CancelacionCreate, EstadoReserva, PagoCreate, ReservaCreate, ReservaResponse
from ..services import reservas as svc
from ..utils import a_json, no_encontrado

router = APIRouter(prefix="/reservas", tags=["Reservas"])

RESUMEN = {"codigo": 1, "estado": 1, "fecha_creacion": 1, "total": 1, "total_pagado": 1, "saldo": 1,
           "cliente.nombre": 1, "cliente.documento": 1, "asesor.codigo": 1, "asesor.nombre": 1,
           "num_pasajeros": 1, "items.descripcion": 1}


@router.get("/", response_model=list[ReservaResponse])
def listar_reservas(estado: Optional[EstadoReserva] = None,
                    cliente: Optional[str] = Query(None, description="Documento del cliente"),
                    asesor: Optional[str] = Query(None, description="Código del asesor"),
                    limit: int = Query(100, le=500),
                    db: Database = Depends(get_db)):
    filtro: dict = {}
    if estado:
        filtro["estado"] = estado
    if cliente:
        filtro["cliente.documento"] = cliente
    if asesor:
        filtro["asesor.codigo"] = asesor
    return a_json(list(db.reservas.find(filtro, RESUMEN).sort("fecha_creacion", -1).limit(limit)))


@router.post("/", response_model=ReservaResponse, status_code=201)
def crear_reserva(datos: ReservaCreate, db: Database = Depends(get_db)):
    return a_json(svc.crear_reserva(db, datos))


@router.get("/{codigo}", response_model=ReservaResponse)
def detalle_reserva(codigo: str, db: Database = Depends(get_db)):
    r = db.reservas.find_one({"codigo": codigo})
    if not r:
        raise no_encontrado(f"No existe la reserva {codigo}")
    return a_json(r)


@router.post("/{codigo}/pagos", response_model=ReservaResponse, status_code=201)
def registrar_pago(codigo: str, pago: PagoCreate, db: Database = Depends(get_db)):
    return a_json(svc.registrar_pago(db, codigo, pago))


@router.post("/{codigo}/cancelar", response_model=ReservaResponse)
def cancelar_reserva(codigo: str, datos: CancelacionCreate, db: Database = Depends(get_db)):
    return a_json(svc.cancelar_reserva(db, codigo, datos))
