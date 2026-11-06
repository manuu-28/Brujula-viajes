"""Funciones de apoyo: ObjectId <-> texto, fechas y errores HTTP."""
from datetime import date, datetime, time, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException


def a_json(valor: Any) -> Any:
    """Convierte recursivamente ObjectId a str y renombra _id -> id."""
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, list):
        return [a_json(v) for v in valor]
    if isinstance(valor, dict):
        salida = {}
        for k, v in valor.items():
            salida["id" if k == "_id" else k] = a_json(v)
        return salida
    return valor


def oid(texto: str, recurso: str = "recurso") -> ObjectId:
    try:
        return ObjectId(texto)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=f"No existe {recurso} con id '{texto}'")


def ahora() -> datetime:
    """Fecha y hora actual en UTC (sin tzinfo, como la devuelve PyMongo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def a_medianoche(d: date | datetime) -> datetime:
    if isinstance(d, datetime):
        d = d.date()
    return datetime.combine(d, time.min)


def conflicto(mensaje: str) -> HTTPException:
    return HTTPException(status_code=409, detail=mensaje)


def no_encontrado(mensaje: str) -> HTTPException:
    return HTTPException(status_code=404, detail=mensaje)
