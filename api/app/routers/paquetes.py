from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from ..database import get_db
from ..schemas import PaqueteCreate, Respuesta
from ..services import inventario
from ..services.reservas import ciudad_ref, item_paquete
from ..utils import a_json, a_medianoche, ahora, conflicto, no_encontrado, oid

router = APIRouter(prefix="/paquetes", tags=["Paquetes"])


def cotizar(db: Database, p: dict, personas: int) -> dict:
    """Precio actual (suma de componentes - descuento) y si TODOS los componentes tienen cupo."""
    try:
        item = item_paquete(db, p["codigo"], personas, ahora())
        inventario.verificar(db, inventario.operaciones_de_items([item]))
        return {"personas": personas, "suma_componentes": item["suma_componentes"],
                "precio": item["subtotal"], "disponible": True, "motivo": None}
    except HTTPException as e:
        return {"personas": personas, "disponible": False, "motivo": e.detail}


@router.get("/", response_model=list[Respuesta])
def listar_paquetes(destino: Optional[str] = Query(None, description="IATA del destino"),
                    solo_vigentes: bool = True,
                    personas: int = Query(2, ge=1, le=20, description="Personas para cotizar"),
                    db: Database = Depends(get_db)):
    filtro: dict = {}
    if destino:
        filtro["destino.iata"] = destino.upper()
    if solo_vigentes:
        hoy = a_medianoche(ahora())
        filtro["vigencia.desde"] = {"$lte": ahora()}
        filtro["vigencia.hasta"] = {"$gte": hoy}
    paquetes = list(db.paquetes.find(filtro).sort("nombre", 1))
    for p in paquetes:
        p["cotizacion"] = cotizar(db, p, personas)
    return a_json(paquetes)


@router.get("/{codigo}", response_model=Respuesta)
def obtener_paquete(codigo: str, personas: int = Query(2, ge=1, le=20), db: Database = Depends(get_db)):
    p = db.paquetes.find_one({"codigo": codigo})
    if not p:
        raise no_encontrado(f"No existe el paquete {codigo}")
    p["cotizacion"] = cotizar(db, p, personas)
    return a_json(p)


@router.post("/", response_model=Respuesta, status_code=201)
def crear_paquete(datos: PaqueteCreate, db: Database = Depends(get_db)):
    if db.paquetes.find_one({"codigo": datos.codigo}, {"_id": 1}):
        raise conflicto(f"Ya existe el paquete {datos.codigo}")
    componentes = []
    for c in datos.componentes:
        if c.tipo == "vuelo":
            v = db.vuelos.find_one({"codigo": c.vuelo_codigo})
            if not v:
                raise no_encontrado(f"No existe el vuelo {c.vuelo_codigo}")
            t = next((t for t in v["tarifas"] if t["tipo"] == c.tarifa), None)
            if not t:
                raise conflicto(f"El vuelo {v['codigo']} no ofrece la tarifa {c.tarifa}")
            componentes.append({
                "tipo": "vuelo", "vuelo_id": v["_id"], "vuelo_codigo": v["codigo"], "tarifa": c.tarifa,
                "fecha": v["salida"], "precio_referencia": t["precio"],
                "descripcion": f"Vuelo {v['codigo']} {v['origen']['iata']}→{v['destino']['iata']} {v['salida']:%Y-%m-%d %H:%M}"})
        elif c.tipo == "hotel":
            h = db.hoteles.find_one({"_id": oid(c.hotel_id, "hotel")})
            if not h:
                raise no_encontrado(f"No existe el hotel {c.hotel_id}")
            th = next((x for x in h["tipos_habitacion"] if x["tipo"] == c.tipo_habitacion), None)
            if not th:
                raise conflicto(f"El hotel {h['nombre']} no tiene habitaciones {c.tipo_habitacion}")
            componentes.append({
                "tipo": "hotel", "hotel_id": h["_id"], "hotel_nombre": h["nombre"], "tipo_habitacion": th["tipo"],
                "capacidad": th["capacidad"], "fecha_entrada": a_medianoche(c.fecha_entrada), "noches": c.noches,
                "precio_referencia": th["precio_noche"],
                "descripcion": f"{c.noches} noches en {h['nombre']} ({th['tipo']}) desde {c.fecha_entrada}"})
        else:
            t = db.tours.find_one({"_id": oid(c.tour_id, "tour")})
            if not t:
                raise no_encontrado(f"No existe el tour {c.tour_id}")
            s = next((s for s in t["salidas"] if s["salida_id"] == c.salida_id), None)
            if not s:
                raise no_encontrado(f"El tour {t['nombre']} no tiene la salida {c.salida_id}")
            componentes.append({
                "tipo": "tour", "tour_id": t["_id"], "tour_nombre": t["nombre"], "salida_id": s["salida_id"],
                "fecha": s["fecha"], "precio_referencia": s["precio"],
                "descripcion": f"Tour {t['nombre']} {s['fecha']:%Y-%m-%d %H:%M}"})
    doc = {
        "codigo": datos.codigo, "nombre": datos.nombre, "destino": ciudad_ref(db, datos.destino),
        "descuento_pct": datos.descuento_pct,
        "vigencia": {"desde": a_medianoche(datos.vigencia_desde), "hasta": a_medianoche(datos.vigencia_hasta)},
        "componentes": componentes,
    }
    db.paquetes.insert_one(doc)
    return a_json(doc)
