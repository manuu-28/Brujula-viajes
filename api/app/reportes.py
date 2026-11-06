"""Pipelines de agregación de los reportes B1 a B3."""
from datetime import datetime

TZ = "America/Bogota"
NO_CANCELADAS = {"estado": {"$ne": "Cancelada"}}


def pipeline_ventas_por_mes(desde: datetime | None = None, hasta: datetime | None = None) -> list[dict]:
    match: dict = dict(NO_CANCELADAS)
    if desde or hasta:
        match["fecha_creacion"] = {**({"$gte": desde} if desde else {}), **({"$lt": hasta} if hasta else {})}
    return [
        {"$match": match},
        {"$group": {
            "_id": {"anio": {"$year": {"date": "$fecha_creacion", "timezone": TZ}},
                    "mes": {"$month": {"date": "$fecha_creacion", "timezone": TZ}}},
            "total_vendido": {"$sum": "$total"},
            "total_recaudado": {"$sum": "$total_pagado"},
            "reservas": {"$sum": 1},
        }},
        {"$sort": {"_id.anio": 1, "_id.mes": 1}},
        {"$project": {
            "_id": 0,
            "anio": "$_id.anio",
            "mes": "$_id.mes",
            "periodo": {"$dateToString": {"format": "%Y-%m",
                                          "date": {"$dateFromParts": {"year": "$_id.anio", "month": "$_id.mes"}}}},
            "reservas": 1,
            "total_vendido": 1,
            "total_recaudado": 1,
            "ticket_promedio": {"$round": [{"$divide": ["$total_vendido", "$reservas"]}, 0]},
        }},
    ]


def pipeline_destinos_mas_vendidos(top: int = 5) -> list[dict]:
    return [
        {"$match": NO_CANCELADAS},
        {"$unwind": "$items"},
        {"$group": {
            "_id": {"reserva": "$_id", "iata": "$items.destino.iata"},
            "ciudad": {"$first": "$items.destino.nombre"},
            "ingresos": {"$sum": "$items.subtotal"},
            "pasajeros": {"$first": "$num_pasajeros"},
        }},
        {"$group": {
            "_id": "$_id.iata",
            "ciudad": {"$first": "$ciudad"},
            "ingresos": {"$sum": "$ingresos"},
            "pasajeros": {"$sum": "$pasajeros"},
            "reservas": {"$sum": 1},
        }},
        {"$sort": {"ingresos": -1}},
        {"$limit": top},
        {"$project": {"_id": 0, "iata": "$_id", "ciudad": 1, "ingresos": 1, "pasajeros": 1, "reservas": 1}},
    ]


def pipeline_ocupacion_vuelos() -> list[dict]:
    """Se calcula sobre el inventario: como al cancelar se devuelven las sillas,"""
    return [
        {"$project": {
            "_id": 0,
            "codigo": 1,
            "aerolinea": 1,
            "salida": 1,
            "ruta": {"$concat": ["$origen.iata", " → ", "$destino.iata"]},
            "sillas_totales": {"$sum": "$tarifas.sillas_totales"},
            "sillas_disponibles": {"$sum": "$tarifas.sillas_disponibles"},
        }},
        {"$project": {
            "codigo": 1, "aerolinea": 1, "salida": 1, "ruta": 1, "sillas_totales": 1,
            "sillas_vendidas": {"$subtract": ["$sillas_totales", "$sillas_disponibles"]},
            "ocupacion_pct": {"$cond": [
                {"$gt": ["$sillas_totales", 0]},
                {"$round": [{"$multiply": [
                    {"$divide": [{"$subtract": ["$sillas_totales", "$sillas_disponibles"]}, "$sillas_totales"]},
                    100]}, 1]},
                0]},
        }},
        {"$sort": {"ocupacion_pct": -1, "salida": 1}},
    ]
