from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from ..database import get_db
from ..schemas import Respuesta, TourCreate
from ..services.reservas import ciudad_ref
from ..utils import a_json, a_medianoche, ahora, no_encontrado, oid

router = APIRouter(prefix="/tours", tags=["Tours"])


@router.get("/", response_model=list[Respuesta])
def buscar_tours(ciudad: Optional[str] = Query(None, description="IATA de la ciudad"),
                 fecha: Optional[date] = Query(None, description="Día de la salida"),
                 db: Database = Depends(get_db)):
    filtro: dict = {}
    if ciudad:
        filtro["ciudad.iata"] = ciudad.upper()
    if fecha:
        inicio, fin = a_medianoche(fecha), a_medianoche(fecha) + timedelta(days=1)
    else:
        inicio, fin = ahora(), None
    rango = {"$gte": inicio, **({"$lt": fin} if fin else {})}
    filtro["salidas"] = {"$elemMatch": {"fecha": rango}}
    tours = list(db.tours.find(filtro).sort("nombre", 1))
    for t in tours:
        t["salidas"] = [s for s in t["salidas"] if s["fecha"] >= inicio and (fin is None or s["fecha"] < fin)]
    return a_json(tours)


@router.get("/{tour_id}", response_model=Respuesta)
def obtener_tour(tour_id: str, db: Database = Depends(get_db)):
    t = db.tours.find_one({"_id": oid(tour_id, "tour")})
    if not t:
        raise no_encontrado(f"No existe el tour {tour_id}")
    return a_json(t)


@router.post("/", response_model=Respuesta, status_code=201)
def crear_tour(datos: TourCreate, db: Database = Depends(get_db)):
    pe = datos.punto_encuentro
    salidas = sorted(datos.salidas, key=lambda s: s.fecha)
    doc = {
        "nombre": datos.nombre,
        "ciudad": ciudad_ref(db, datos.ciudad),
        "descripcion": datos.descripcion,
        "duracion_horas": datos.duracion_horas,
        "incluye": datos.incluye,
        "punto_encuentro": {"nombre": pe.nombre, "ubicacion": {"type": "Point", "coordinates": [pe.longitud, pe.latitud]}},
        "salidas": [{"salida_id": f"S{s.fecha:%Y%m%d%H%M}", "fecha": s.fecha.replace(tzinfo=None), "precio": s.precio,
                     "cupos_totales": s.cupos, "cupos_disponibles": s.cupos} for s in salidas],
    }
    db.tours.insert_one(doc)
    return a_json(doc)
