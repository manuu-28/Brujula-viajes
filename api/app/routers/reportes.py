from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from .. import reportes as rp
from ..database import get_db
from ..utils import a_medianoche

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("/ventas-por-mes", summary="B1. Total vendido y número de reservas por mes")
def ventas_por_mes(desde: Optional[date] = None, hasta: Optional[date] = None, db: Database = Depends(get_db)):
    pipeline = rp.pipeline_ventas_por_mes(a_medianoche(desde) if desde else None, a_medianoche(hasta) if hasta else None)
    return list(db.reservas.aggregate(pipeline))


@router.get("/destinos-mas-vendidos", summary="B2. Top de ciudades de destino por ingresos")
def destinos_mas_vendidos(top: int = Query(5, ge=1, le=20), db: Database = Depends(get_db)):
    return list(db.reservas.aggregate(rp.pipeline_destinos_mas_vendidos(top)))


@router.get("/ocupacion-vuelos", summary="B3. Ocupación por vuelo, de mayor a menor")
def ocupacion_vuelos(db: Database = Depends(get_db)):
    return list(db.vuelos.aggregate(rp.pipeline_ocupacion_vuelos()))
