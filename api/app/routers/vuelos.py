from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from ..database import get_db
from ..schemas import Respuesta, VueloCreate
from ..services.reservas import ciudad_ref
from ..utils import a_json, a_medianoche, ahora, conflicto, no_encontrado

router = APIRouter(prefix="/vuelos", tags=["Vuelos"])


def _resumen(v: dict) -> dict:
    v["sillas_disponibles"] = sum(t["sillas_disponibles"] for t in v["tarifas"])
    v["precio_desde"] = min(t["precio"] for t in v["tarifas"])
    return a_json(v)


@router.get("/", response_model=list[Respuesta])
def buscar_vuelos(origen: Optional[str] = Query(None, description="IATA de origen"),
                  destino: Optional[str] = Query(None, description="IATA de destino"),
                  fecha: Optional[date] = Query(None, description="Día de salida"),
                  incluir_pasados: bool = False,
                  db: Database = Depends(get_db)):
    filtro: dict = {}
    if origen:
        filtro["origen.iata"] = origen.upper()
    if destino:
        filtro["destino.iata"] = destino.upper()
    if fecha:
        inicio = a_medianoche(fecha)
        filtro["salida"] = {"$gte": inicio, "$lt": inicio + timedelta(days=1)}
    elif not incluir_pasados:
        filtro["salida"] = {"$gte": ahora()}
    return [_resumen(v) for v in db.vuelos.find(filtro).sort("salida", 1).limit(300)]


@router.get("/{codigo}", response_model=Respuesta)
def obtener_vuelo(codigo: str, db: Database = Depends(get_db)):
    v = db.vuelos.find_one({"codigo": codigo.upper()})
    if not v:
        raise no_encontrado(f"No existe el vuelo {codigo}")
    return _resumen(v)


@router.post("/", response_model=Respuesta, status_code=201)
def crear_vuelo(datos: VueloCreate, db: Database = Depends(get_db)):
    if db.vuelos.find_one({"codigo": datos.codigo}, {"_id": 1}):
        raise conflicto(f"Ya existe el vuelo {datos.codigo}")
    doc = {
        "codigo": datos.codigo,
        "aerolinea": datos.aerolinea,
        "origen": ciudad_ref(db, datos.origen),
        "destino": ciudad_ref(db, datos.destino),
        "salida": datos.salida.replace(tzinfo=None),
        "llegada": datos.llegada.replace(tzinfo=None),
        "tarifas": [{"tipo": t.tipo, "precio": t.precio, "equipaje": t.equipaje,
                     "sillas_totales": t.sillas, "sillas_disponibles": t.sillas} for t in datos.tarifas],
    }
    db.vuelos.insert_one(doc)
    return _resumen(doc)
