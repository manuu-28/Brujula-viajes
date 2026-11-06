"""Reglas de negocio de las reservas: creación, pagos y cancelación."""
import math
from datetime import datetime, timedelta

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.database import Database

from ..schemas import CancelacionCreate, ItemIn, PagoCreate, ReservaCreate
from ..utils import a_medianoche, ahora, conflicto, no_encontrado, oid
from . import inventario


def _num(x: float) -> int | float:
    """Precios en pesos: se guardan como entero cuando no tienen decimales."""
    return int(x) if float(x).is_integer() else round(x, 2)


def ciudad_ref(db: Database, iata: str) -> dict:
    c = db.ciudades.find_one({"_id": iata})
    if not c:
        raise HTTPException(status_code=422, detail=f"La ciudad '{iata}' no está registrada")
    return {"iata": c["_id"], "nombre": c["nombre"]}


def item_vuelo(db: Database, codigo: str, tarifa: str, cantidad: int, momento: datetime) -> dict:
    v = db.vuelos.find_one({"codigo": codigo})
    if not v:
        raise no_encontrado(f"No existe el vuelo {codigo}")
    t = next((t for t in v["tarifas"] if t["tipo"] == tarifa), None)
    if not t:
        raise conflicto(f"El vuelo {codigo} no ofrece la tarifa {tarifa}")
    if v["salida"] <= momento:
        raise conflicto(f"El vuelo {codigo} ya salió ({v['salida']:%Y-%m-%d %H:%M})")
    return {
        "tipo": "vuelo",
        "vuelo_id": v["_id"],
        "vuelo_codigo": v["codigo"],
        "aerolinea": v["aerolinea"],
        "tarifa": tarifa,
        "equipaje": t["equipaje"],
        "ruta": {"origen": v["origen"], "destino": v["destino"]},
        "destino": v["destino"],
        "fecha_servicio": v["salida"],
        "descripcion": f"Vuelo {v['codigo']} {v['origen']['iata']}→{v['destino']['iata']} "
                       f"{v['salida']:%Y-%m-%d %H:%M} · {tarifa}",
        "cantidad": cantidad,
        "precio_unitario": _num(t["precio"]),
        "subtotal": _num(t["precio"] * cantidad),
    }


def item_hotel(db: Database, hotel_id: str, tipo: str, fecha_entrada, noches: int, cantidad: int,
               momento: datetime) -> dict:
    h = db.hoteles.find_one({"_id": oid(hotel_id, "hotel")})
    if not h:
        raise no_encontrado(f"No existe el hotel {hotel_id}")
    th = next((x for x in h["tipos_habitacion"] if x["tipo"] == tipo), None)
    if not th:
        raise conflicto(f"El hotel {h['nombre']} no tiene habitaciones {tipo}")
    entrada = a_medianoche(fecha_entrada)
    if entrada < a_medianoche(momento):
        raise conflicto(f"La fecha de entrada {entrada:%Y-%m-%d} ya pasó")
    return {
        "tipo": "hotel",
        "hotel_id": h["_id"],
        "hotel_nombre": h["nombre"],
        "categoria": h["categoria"],
        "tipo_habitacion": tipo,
        "capacidad": th["capacidad"],
        "fecha_entrada": entrada,
        "fecha_salida": entrada + timedelta(days=noches),
        "noches": noches,
        "destino": h["ciudad"],
        "fecha_servicio": entrada,
        "descripcion": f"{h['nombre']} · {cantidad} hab. {tipo} · {noches} noches desde {entrada:%Y-%m-%d}",
        "cantidad": cantidad,
        "precio_unitario": _num(th["precio_noche"]),
        "subtotal": _num(th["precio_noche"] * noches * cantidad),
    }


def item_tour(db: Database, tour_id: str, salida_id: str, cantidad: int, momento: datetime) -> dict:
    t = db.tours.find_one({"_id": oid(tour_id, "tour")})
    if not t:
        raise no_encontrado(f"No existe el tour {tour_id}")
    s = next((s for s in t["salidas"] if s["salida_id"] == salida_id), None)
    if not s:
        raise no_encontrado(f"El tour {t['nombre']} no tiene la salida {salida_id}")
    if s["fecha"] <= momento:
        raise conflicto(f"La salida {s['fecha']:%Y-%m-%d %H:%M} del tour {t['nombre']} ya pasó")
    return {
        "tipo": "tour",
        "tour_id": t["_id"],
        "tour_nombre": t["nombre"],
        "salida_id": salida_id,
        "duracion_horas": t["duracion_horas"],
        "destino": t["ciudad"],
        "fecha_servicio": s["fecha"],
        "descripcion": f"Tour {t['nombre']} · {s['fecha']:%Y-%m-%d %H:%M}",
        "cantidad": cantidad,
        "precio_unitario": _num(s["precio"]),
        "subtotal": _num(s["precio"] * cantidad),
    }


def item_paquete(db: Database, codigo: str, personas: int, momento: datetime) -> dict:
    p = db.paquetes.find_one({"codigo": codigo})
    if not p:
        raise no_encontrado(f"No existe el paquete {codigo}")
    if not (p["vigencia"]["desde"] <= momento <= p["vigencia"]["hasta"] + timedelta(days=1)):
        raise conflicto(f"El paquete {p['nombre']} no está vigente "
                        f"({p['vigencia']['desde']:%Y-%m-%d} a {p['vigencia']['hasta']:%Y-%m-%d})")
    componentes = []
    for c in p["componentes"]:
        if c["tipo"] == "vuelo":
            componentes.append(item_vuelo(db, c["vuelo_codigo"], c["tarifa"], personas, momento))
        elif c["tipo"] == "hotel":
            habitaciones = math.ceil(personas / c["capacidad"])
            componentes.append(item_hotel(db, str(c["hotel_id"]), c["tipo_habitacion"], c["fecha_entrada"],
                                          c["noches"], habitaciones, momento))
        else:
            componentes.append(item_tour(db, str(c["tour_id"]), c["salida_id"], personas, momento))
    marcar_regresos(componentes)
    suma = sum(c["subtotal"] for c in componentes)
    precio = _num(round(suma * (1 - p["descuento_pct"] / 100)))
    return {
        "tipo": "paquete",
        "paquete_id": p["_id"],
        "paquete_codigo": p["codigo"],
        "paquete_nombre": p["nombre"],
        "destino": p["destino"],
        "fecha_servicio": min(c["fecha_servicio"] for c in componentes),
        "descripcion": f"Paquete {p['nombre']} · {personas} persona(s)",
        "personas": personas,
        "descuento_pct": p["descuento_pct"],
        "suma_componentes": _num(suma),
        "cantidad": 1,
        "precio_unitario": precio,
        "subtotal": precio,
        "componentes": componentes,
    }


def marcar_regresos(items: list[dict]) -> None:
    """Un vuelo CTG→BOG que regresa de un BOG→CTG anterior en la misma reserva"""
    vuelos = [i for i in items if i["tipo"] == "vuelo"]
    for i in vuelos:
        for j in vuelos:
            if (j is not i and j["fecha_servicio"] < i["fecha_servicio"]
                    and j["ruta"]["origen"]["iata"] == i["ruta"]["destino"]["iata"]
                    and j["ruta"]["destino"]["iata"] == i["ruta"]["origen"]["iata"]):
                i["destino"] = i["ruta"]["origen"]
                i["tramo"] = "regreso"
                break
        else:
            i["tramo"] = "ida"


def construir_item(db: Database, it: ItemIn, momento: datetime) -> dict:
    if it.tipo == "vuelo":
        return item_vuelo(db, it.vuelo_codigo, it.tarifa, it.cantidad, momento)
    if it.tipo == "hotel":
        return item_hotel(db, it.hotel_id, it.tipo_habitacion, it.fecha_entrada, it.noches, it.cantidad, momento)
    if it.tipo == "tour":
        return item_tour(db, it.tour_id, it.salida_id, it.cantidad, momento)
    return item_paquete(db, it.paquete_codigo, it.cantidad, momento)


def siguiente_codigo(db: Database) -> str:
    c = db.contadores.find_one_and_update({"_id": "reservas"}, {"$inc": {"seq": 1}},
                                          upsert=True, return_document=ReturnDocument.AFTER)
    return f"RSV-{c['seq']:06d}"


def crear_reserva(db: Database, datos: ReservaCreate, fecha_creacion: datetime | None = None) -> dict:
    momento = ahora()
    fecha = fecha_creacion or momento
    cliente = db.clientes.find_one({"documento": datos.cliente_documento})
    if not cliente:
        raise no_encontrado(f"No existe un cliente con documento {datos.cliente_documento}")
    asesor = db.asesores.find_one({"codigo": datos.asesor_codigo, "activo": True})
    if not asesor:
        raise no_encontrado(f"No existe un asesor activo con código {datos.asesor_codigo}")
    usuario = datos.usuario or asesor["usuario"]

    items = [construir_item(db, it, momento) for it in datos.items]
    marcar_regresos(items)
    ops = inventario.operaciones_de_items(items)
    inventario.verificar(db, ops)
    inventario.descontar(db, ops)

    total = _num(sum(i["subtotal"] for i in items))
    doc = {
        "codigo": siguiente_codigo(db),
        "cliente": {"cliente_id": cliente["_id"], "documento": cliente["documento"],
                    "nombre": cliente["nombre"], "correo": cliente["correo"], "telefono": cliente["telefono"]},
        "asesor": {"asesor_id": asesor["_id"], "codigo": asesor["codigo"], "nombre": asesor["nombre"]},
        "fecha_creacion": fecha,
        "estado": "Pendiente",
        "items": items,
        "pasajeros": [{"nombre": p.nombre, "documento": p.documento,
                       "fecha_nacimiento": a_medianoche(p.fecha_nacimiento)} for p in datos.pasajeros],
        "num_pasajeros": len(datos.pasajeros),
        "total": total,
        "total_pagado": 0,
        "saldo": total,
        "pagos": [],
        "historial": [{"fecha": fecha, "estado_anterior": None, "estado_nuevo": "Pendiente",
                       "usuario": usuario, "nota": "Reserva creada; cupos apartados"}],
    }
    try:
        db.reservas.insert_one(doc)
    except Exception:
        inventario.devolver(db, ops)
        raise
    return doc


def registrar_pago(db: Database, codigo: str, pago: PagoCreate, fecha: datetime | None = None) -> dict:
    fecha = fecha or ahora()
    r = db.reservas.find_one({"codigo": codigo})
    if not r:
        raise no_encontrado(f"No existe la reserva {codigo}")
    if r["estado"] == "Cancelada":
        raise conflicto(f"No se aceptan pagos: la reserva {codigo} está cancelada")
    if r["estado"] == "Pagada":
        raise conflicto(f"La reserva {codigo} ya está pagada en su totalidad")
    saldo = r["total"] - r["total_pagado"]
    if pago.valor > saldo:
        raise conflicto(f"El pago ({pago.valor:,.0f}) supera el saldo pendiente ({saldo:,.0f})")

    nuevo_pagado = _num(r["total_pagado"] + pago.valor)
    actualizacion: dict = {
        "$push": {"pagos": {"fecha": fecha, "valor": _num(pago.valor), "medio": pago.medio, "usuario": pago.usuario}},
        "$set": {"total_pagado": nuevo_pagado, "saldo": _num(r["total"] - nuevo_pagado)},
    }
    if nuevo_pagado >= r["total"]:
        actualizacion["$set"]["estado"] = "Pagada"
        actualizacion["$push"]["historial"] = {
            "fecha": fecha, "estado_anterior": "Pendiente", "estado_nuevo": "Pagada",
            "usuario": pago.usuario, "nota": f"Pagos cubren el total ({len(r['pagos']) + 1} pago(s))"}
    res = db.reservas.update_one({"_id": r["_id"], "estado": "Pendiente", "total_pagado": r["total_pagado"]},
                                 actualizacion)
    if res.modified_count != 1:
        raise conflicto("La reserva cambió mientras se registraba el pago. Consulte de nuevo e intente otra vez.")
    return db.reservas.find_one({"_id": r["_id"]})


def cancelar_reserva(db: Database, codigo: str, datos: CancelacionCreate, fecha: datetime | None = None) -> dict:
    fecha = fecha or ahora()
    r = db.reservas.find_one({"codigo": codigo})
    if not r:
        raise no_encontrado(f"No existe la reserva {codigo}")
    if r["estado"] == "Cancelada":
        raise conflicto(f"La reserva {codigo} ya estaba cancelada")
    res = db.reservas.update_one(
        {"_id": r["_id"], "estado": r["estado"]},
        {"$set": {"estado": "Cancelada", "fecha_cancelacion": fecha},
         "$push": {"historial": {"fecha": fecha, "estado_anterior": r["estado"], "estado_nuevo": "Cancelada",
                                 "usuario": datos.usuario, "nota": datos.motivo or "Cancelada; cupos devueltos"}}})
    if res.modified_count != 1:
        raise conflicto("La reserva cambió mientras se cancelaba. Consulte de nuevo.")
    inventario.devolver(db, inventario.operaciones_de_items(r["items"]))
    return db.reservas.find_one({"_id": r["_id"]})
