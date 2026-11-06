"""Inventario: verificación, descuento ($inc) y devolución de cupos."""
from collections import OrderedDict
from datetime import datetime, timedelta

from pymongo.database import Database

from ..utils import conflicto


class SinDisponibilidad(Exception):
    pass


def _clave(op: dict) -> tuple:
    if op["tipo"] == "vuelo":
        return ("vuelo", op["vuelo_id"], op["tarifa"])
    if op["tipo"] == "hotel":
        return ("hotel", op["hotel_id"], op["tipo_habitacion"], op["fecha"])
    return ("tour", op["tour_id"], op["salida_id"])


def noches(fecha_entrada: datetime, cantidad_noches: int) -> list[datetime]:
    return [fecha_entrada + timedelta(days=i) for i in range(cantidad_noches)]


def operaciones_de_items(items: list[dict]) -> list[dict]:
    """Deriva las operaciones de inventario a partir de los ítems guardados en la reserva."""
    ops: list[dict] = []

    def agregar(comp: dict) -> None:
        if comp["tipo"] == "vuelo":
            ops.append({"tipo": "vuelo", "vuelo_id": comp["vuelo_id"], "tarifa": comp["tarifa"],
                        "cantidad": comp["cantidad"], "etiqueta": f"vuelo {comp['vuelo_codigo']}"})
        elif comp["tipo"] == "hotel":
            for f in noches(comp["fecha_entrada"], comp["noches"]):
                ops.append({"tipo": "hotel", "hotel_id": comp["hotel_id"], "tipo_habitacion": comp["tipo_habitacion"],
                            "fecha": f, "cantidad": comp["cantidad"], "etiqueta": comp["hotel_nombre"]})
        elif comp["tipo"] == "tour":
            ops.append({"tipo": "tour", "tour_id": comp["tour_id"], "salida_id": comp["salida_id"],
                        "cantidad": comp["cantidad"], "etiqueta": comp["tour_nombre"]})

    for item in items:
        if item["tipo"] == "paquete":
            for comp in item["componentes"]:
                agregar(comp)
        else:
            agregar(item)
    return ops


def agrupar(ops: list[dict]) -> list[dict]:
    grupos: "OrderedDict[tuple, dict]" = OrderedDict()
    for op in ops:
        k = _clave(op)
        if k in grupos:
            grupos[k]["cantidad"] += op["cantidad"]
        else:
            grupos[k] = dict(op)
    return list(grupos.values())


def verificar(db: Database, ops: list[dict]) -> None:
    """Lanza HTTP 409 con un mensaje claro si alguna operación no tiene cupo."""
    for op in agrupar(ops):
        n = op["cantidad"]
        if op["tipo"] == "vuelo":
            v = db.vuelos.find_one({"_id": op["vuelo_id"]}, {"codigo": 1, "tarifas": 1})
            tarifa = next((t for t in (v or {}).get("tarifas", []) if t["tipo"] == op["tarifa"]), None)
            disp = tarifa["sillas_disponibles"] if tarifa else 0
            if disp < n:
                raise conflicto(f"Sin disponibilidad: {op['etiqueta']}, tarifa {op['tarifa']} "
                                f"(quedan {disp} sillas, se piden {n})")
        elif op["tipo"] == "hotel":
            d = db.disponibilidad_hotel.find_one(
                {"hotel_id": op["hotel_id"], "tipo": op["tipo_habitacion"], "fecha": op["fecha"]})
            disp = d["libres"] if d else 0
            if disp < n:
                raise conflicto(f"Sin disponibilidad: {op['etiqueta']}, habitación {op['tipo_habitacion']}, "
                                f"noche {op['fecha']:%Y-%m-%d} (libres {disp}, se piden {n})")
        else:
            t = db.tours.find_one({"_id": op["tour_id"]}, {"salidas": 1})
            salida = next((s for s in (t or {}).get("salidas", []) if s["salida_id"] == op["salida_id"]), None)
            disp = salida["cupos_disponibles"] if salida else 0
            if disp < n:
                fecha = f" {salida['fecha']:%Y-%m-%d %H:%M}" if salida else ""
                raise conflicto(f"Sin disponibilidad: tour {op['etiqueta']}, salida{fecha} "
                                f"(quedan {disp} cupos, se piden {n})")


def _aplicar(db: Database, op: dict, signo: int) -> bool:
    n = op["cantidad"]
    if op["tipo"] == "vuelo":
        filtro = {"_id": op["vuelo_id"],
                  "tarifas": {"$elemMatch": {"tipo": op["tarifa"], **({"sillas_disponibles": {"$gte": n}} if signo < 0 else {})}}}
        r = db.vuelos.update_one(filtro, {"$inc": {"tarifas.$.sillas_disponibles": signo * n}})
    elif op["tipo"] == "hotel":
        filtro = {"hotel_id": op["hotel_id"], "tipo": op["tipo_habitacion"], "fecha": op["fecha"]}
        if signo < 0:
            filtro["libres"] = {"$gte": n}
        r = db.disponibilidad_hotel.update_one(filtro, {"$inc": {"libres": signo * n}})
    else:
        filtro = {"_id": op["tour_id"],
                  "salidas": {"$elemMatch": {"salida_id": op["salida_id"], **({"cupos_disponibles": {"$gte": n}} if signo < 0 else {})}}}
        r = db.tours.update_one(filtro, {"$inc": {"salidas.$.cupos_disponibles": signo * n}})
    return r.modified_count == 1


def descontar(db: Database, ops: list[dict]) -> None:
    """Descuenta todo el inventario o nada (compensa si algo falla)."""
    aplicadas: list[dict] = []
    for op in agrupar(ops):
        if _aplicar(db, op, -1):
            aplicadas.append(op)
        else:
            for hecha in reversed(aplicadas):
                _aplicar(db, hecha, +1)
            raise conflicto(f"Sin disponibilidad: {op['etiqueta']} se agotó mientras se procesaba la reserva. "
                            "Intente de nuevo.")


def devolver(db: Database, ops: list[dict]) -> None:
    for op in agrupar(ops):
        _aplicar(db, op, +1)
