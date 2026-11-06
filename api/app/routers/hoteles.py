from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from ..database import get_db
from ..schemas import HotelCreate, Respuesta
from ..services.reservas import ciudad_ref
from ..utils import a_json, a_medianoche, ahora, no_encontrado, oid

router = APIRouter(prefix="/hoteles", tags=["Hoteles"])


def disponibilidad_rango(db: Database, hotel_ids: list, entrada, noches: int) -> dict:
    """Mínimo de habitaciones libres por (hotel, tipo) en TODAS las noches pedidas."""
    inicio = a_medianoche(entrada)
    pipeline = [
        {"$match": {"hotel_id": {"$in": hotel_ids}, "fecha": {"$gte": inicio, "$lt": inicio + timedelta(days=noches)}}},
        {"$group": {"_id": {"hotel_id": "$hotel_id", "tipo": "$tipo"},
                    "min_libres": {"$min": "$libres"}, "noches_abiertas": {"$sum": 1}}},
    ]
    res = {}
    for d in db.disponibilidad_hotel.aggregate(pipeline):
        libres = d["min_libres"] if d["noches_abiertas"] == noches else 0
        res[(d["_id"]["hotel_id"], d["_id"]["tipo"])] = libres
    return res


@router.get("/", response_model=list[Respuesta])
def buscar_hoteles(ciudad: Optional[str] = Query(None, description="IATA de la ciudad"),
                   entrada: Optional[date] = Query(None, description="Fecha de entrada"),
                   noches: int = Query(1, ge=1, le=30),
                   db: Database = Depends(get_db)):
    filtro = {"ciudad.iata": ciudad.upper()} if ciudad else {}
    hoteles = list(db.hoteles.find(filtro).sort("nombre", 1))
    entrada = entrada or ahora().date()
    disp = disponibilidad_rango(db, [h["_id"] for h in hoteles], entrada, noches)
    for h in hoteles:
        for th in h["tipos_habitacion"]:
            th["libres_en_rango"] = disp.get((h["_id"], th["tipo"]), 0)
        h["consulta"] = {"entrada": a_medianoche(entrada), "noches": noches}
    return a_json(hoteles)


@router.get("/{hotel_id}", response_model=Respuesta)
def obtener_hotel(hotel_id: str, db: Database = Depends(get_db)):
    h = db.hoteles.find_one({"_id": oid(hotel_id, "hotel")})
    if not h:
        raise no_encontrado(f"No existe el hotel {hotel_id}")
    return a_json(h)


@router.get("/{hotel_id}/disponibilidad", response_model=list[dict])
def calendario(hotel_id: str, desde: Optional[date] = None, dias: int = Query(30, le=120),
               db: Database = Depends(get_db)):
    inicio = a_medianoche(desde or ahora().date())
    cur = db.disponibilidad_hotel.find(
        {"hotel_id": oid(hotel_id, "hotel"), "fecha": {"$gte": inicio, "$lt": inicio + timedelta(days=dias)}},
        {"_id": 0, "tipo": 1, "fecha": 1, "libres": 1, "total": 1}).sort([("fecha", 1), ("tipo", 1)])
    return list(cur)


@router.post("/", response_model=Respuesta, status_code=201)
def crear_hotel(datos: HotelCreate, db: Database = Depends(get_db)):
    doc = {
        "nombre": datos.nombre,
        "ciudad": ciudad_ref(db, datos.ciudad),
        "direccion": datos.direccion,
        "categoria": datos.categoria,
        "servicios": datos.servicios,
        "ubicacion": {"type": "Point", "coordinates": [datos.longitud, datos.latitud]},
        "tipos_habitacion": [t.model_dump() for t in datos.tipos_habitacion],
    }
    db.hoteles.insert_one(doc)
    hoy = a_medianoche(ahora())
    db.disponibilidad_hotel.insert_many([
        {"hotel_id": doc["_id"], "tipo": t.tipo, "fecha": hoy + timedelta(days=i),
         "total": t.total_habitaciones, "libres": t.total_habitaciones}
        for t in datos.tipos_habitacion for i in range(datos.dias_calendario)
    ])
    return a_json(doc)
