from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from ..database import get_db
from ..schemas import AsesorCreate, CiudadCreate, ClienteCreate, ClienteResponse, Respuesta
from ..utils import a_json, ahora, conflicto, no_encontrado

router = APIRouter(tags=["Clientes, asesores y ciudades"])


@router.get("/clientes/", response_model=list[ClienteResponse])
def listar_clientes(q: Optional[str] = Query(None, description="Texto en nombre o documento"),
                    limit: int = Query(100, le=500), db: Database = Depends(get_db)):
    filtro = {}
    if q:
        filtro = {"$or": [{"nombre": {"$regex": q, "$options": "i"}}, {"documento": {"$regex": f"^{q}"}}]}
    return a_json(list(db.clientes.find(filtro).sort("nombre", 1).limit(limit)))


@router.get("/clientes/{documento}", response_model=ClienteResponse)
def obtener_cliente(documento: str, db: Database = Depends(get_db)):
    c = db.clientes.find_one({"documento": documento})
    if not c:
        raise no_encontrado(f"No existe un cliente con documento {documento}")
    c["reservas_recientes"] = list(db.reservas.find(
        {"cliente.cliente_id": c["_id"]},
        {"_id": 0, "codigo": 1, "estado": 1, "total": 1, "fecha_creacion": 1},
    ).sort("fecha_creacion", -1).limit(10))
    return a_json(c)


@router.post("/clientes/", response_model=ClienteResponse, status_code=201)
def crear_cliente(datos: ClienteCreate, db: Database = Depends(get_db)):
    if db.clientes.find_one({"documento": datos.documento}, {"_id": 1}):
        raise conflicto(f"Ya existe un cliente con documento {datos.documento}")
    doc = datos.model_dump(exclude_none=True)
    doc["fecha_registro"] = ahora()
    db.clientes.insert_one(doc)
    return a_json(doc)


@router.get("/asesores/", response_model=list[Respuesta])
def listar_asesores(db: Database = Depends(get_db)):
    return a_json(list(db.asesores.find().sort("codigo", 1)))


@router.post("/asesores/", response_model=Respuesta, status_code=201)
def crear_asesor(datos: AsesorCreate, db: Database = Depends(get_db)):
    if db.asesores.find_one({"$or": [{"codigo": datos.codigo}, {"usuario": datos.usuario}]}):
        raise conflicto("Ya existe un asesor con ese código o usuario")
    doc = {**datos.model_dump(), "activo": True}
    db.asesores.insert_one(doc)
    return a_json(doc)


@router.get("/ciudades/", response_model=list[Respuesta])
def listar_ciudades(db: Database = Depends(get_db)):
    return [{"id": c["_id"], "iata": c["_id"], **{k: v for k, v in c.items() if k != "_id"}}
            for c in db.ciudades.find().sort("nombre", 1)]


@router.post("/ciudades/", response_model=Respuesta, status_code=201)
def crear_ciudad(datos: CiudadCreate, db: Database = Depends(get_db)):
    if db.ciudades.find_one({"_id": datos.iata}):
        raise conflicto(f"La ciudad {datos.iata} ya existe")
    db.ciudades.insert_one({"_id": datos.iata, "nombre": datos.nombre, "departamento": datos.departamento})
    return {"id": datos.iata, **datos.model_dump()}
