import argparse
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import reportes
from app.database import MONGO_DB, get_database
from app.schemas import CancelacionCreate, ItemIn, PagoCreate, PasajeroIn, ReservaCreate
from app.services import reservas as svc
from app.setup_db import crear_esquema
from app.utils import a_medianoche, ahora

random.seed(2026)
AHORA = ahora()
HOY = a_medianoche(AHORA)


def dia(n: int, hora: int = 0, minuto: int = 0) -> datetime:
    return HOY + timedelta(days=n, hours=hora, minutes=minuto)


CIUDADES = [
    ("BOG", "Bogotá", "Cundinamarca"), ("CTG", "Cartagena", "Bolívar"), ("SMR", "Santa Marta", "Magdalena"),
    ("MDE", "Medellín", "Antioquia"), ("ADZ", "San Andrés", "San Andrés y Providencia"), ("RCH", "Riohacha", "La Guajira"),
]
NOMBRE = {c[0]: c[1] for c in CIUDADES}

ASESORES = [
    {"codigo": "A01", "nombre": "Laura Méndez", "correo": "laura.mendez@brujulaviajes.co", "usuario": "lmendez", "activo": True},
    {"codigo": "A02", "nombre": "Andrés Pineda", "correo": "andres.pineda@brujulaviajes.co", "usuario": "apineda", "activo": True},
    {"codigo": "A03", "nombre": "Camila Rojas", "correo": "camila.rojas@brujulaviajes.co", "usuario": "crojas", "activo": True},
]

NOMBRES_CLIENTES = [
    "María Fernanda Gómez", "Juan Camilo Restrepo", "Valentina Ospina", "Santiago Herrera", "Daniela Castro",
    "Carlos Andrés Ruiz", "Paula Andrea Vargas", "Sebastián Morales", "Natalia Quintero", "Felipe Arango",
    "Isabella Cárdenas", "Mateo Salazar", "Juliana Rincón", "Alejandro Torres", "Sara Lucía Pardo",
]
OTROS_PASAJEROS = ["Martín Gómez", "Lucía Restrepo", "Tomás Ospina", "Elena Herrera", "Simón Castro", "Ana Ruiz",
                   "Pedro Vargas", "Manuela Morales", "Jacobo Quintero", "Laura Arango", "Emilio Cárdenas"]

VUELOS = [
    ("AV9401", "Avianca", "BOG", "CTG", 3, 7, 85, 289000), ("AV9402", "Avianca", "CTG", "BOG", 6, 19, 85, 299000),
    ("AV9403", "Avianca", "BOG", "CTG", 10, 6, 85, 319000), ("AV9404", "Avianca", "CTG", "BOG", 14, 18, 85, 329000),
    ("LA4101", "LATAM", "BOG", "CTG", 17, 9, 85, 259000), ("LA4102", "LATAM", "CTG", "BOG", 21, 20, 85, 269000),
    ("LA4201", "LATAM", "BOG", "SMR", 5, 8, 80, 239000), ("LA4202", "LATAM", "SMR", "BOG", 8, 17, 80, 249000),
    ("LA4203", "LATAM", "BOG", "SMR", 15, 8, 80, 249000), ("LA4204", "LATAM", "SMR", "BOG", 18, 17, 80, 259000),
    ("AV9601", "Avianca", "BOG", "ADZ", 20, 9, 140, 459000), ("AV9602", "Avianca", "ADZ", "BOG", 25, 15, 140, 469000),
    ("P57601", "Wingo", "BOG", "ADZ", 27, 6, 140, 379000), ("P57602", "Wingo", "ADZ", "BOG", 30, 13, 140, 389000),
    ("P57301", "Wingo", "MDE", "CTG", 4, 11, 75, 199000), ("P57302", "Wingo", "CTG", "MDE", 9, 14, 75, 209000),
    ("AV9701", "Avianca", "BOG", "RCH", 7, 7, 100, 349000), ("AV9702", "Avianca", "RCH", "BOG", 11, 16, 100, 359000),
    ("AV9201", "Avianca", "BOG", "MDE", 2, 6, 55, 189000), ("AV9202", "Avianca", "MDE", "BOG", 5, 20, 55, 199000),
]

HOTELES = {
    "murallas": {"nombre": "Hotel Murallas Coloniales", "ciudad": "CTG", "direccion": "Calle del Curato 38-125, Centro Histórico",
                 "categoria": 5, "servicios": ["piscina", "wifi", "desayuno incluido", "spa"], "lat": 10.4236, "lon": -75.5506,
                 "tipos": [("Sencilla", 1, 410000, 3), ("Doble", 2, 520000, 5), ("Suite", 3, 980000, 2)]},
    "bocagrande": {"nombre": "Hotel Bocagrande Mar", "ciudad": "CTG", "direccion": "Av. San Martín 5-80, Bocagrande",
                   "categoria": 4, "servicios": ["piscina", "wifi", "frente al mar"], "lat": 10.4006, "lon": -75.5547,
                   "tipos": [("Sencilla", 1, 260000, 6), ("Doble", 2, 340000, 8), ("Familiar", 4, 520000, 4)]},
    "rodadero": {"nombre": "Hotel Rodadero Sol", "ciudad": "SMR", "direccion": "Carrera 1 # 9-35, El Rodadero",
                 "categoria": 4, "servicios": ["piscina", "wifi", "desayuno incluido"], "lat": 11.2034, "lon": -74.2269,
                 "tipos": [("Doble", 2, 300000, 8), ("Familiar", 4, 480000, 4)]},
    "posada": {"nombre": "Posada Mar Caribe", "ciudad": "ADZ", "direccion": "Av. Colombia 1-19, North End",
               "categoria": 3, "servicios": ["wifi", "desayuno incluido"], "lat": 12.5847, "lon": -81.7006,
               "tipos": [("Doble", 2, 280000, 6), ("Familiar", 4, 450000, 3)]},
    "arena": {"nombre": "Hotel Arena Wayuu", "ciudad": "RCH", "direccion": "Calle 1 # 4-77, Malecón",
              "categoria": 3, "servicios": ["wifi", "aire acondicionado"], "lat": 11.5444, "lon": -72.9072,
              "tipos": [("Sencilla", 1, 180000, 4), ("Doble", 2, 240000, 6)]},
    "poblado": {"nombre": "Hotel Poblado Plaza", "ciudad": "MDE", "direccion": "Carrera 43A # 4 Sur-75, El Poblado",
                "categoria": 4, "servicios": ["piscina", "wifi", "gimnasio"], "lat": 6.2008, "lon": -75.5728,
                "tipos": [("Sencilla", 1, 230000, 6), ("Doble", 2, 310000, 6), ("Suite", 3, 620000, 2)]},
}
DIAS_CALENDARIO = 45

TOURS = {
    "islas": ("Islas del Rosario en lancha", "CTG", 8, 260000, 16, 8, 2, 2, ["lancha", "almuerzo típico", "snorkel"],
              "Muelle La Bodeguita", 10.4229, -75.5482, "Recorrido por el archipiélago con parada en playa y snorkel."),
    "murallas": ("Ciudad amurallada a pie", "CTG", 3, 90000, 20, 16, 2, 3, ["guía bilingüe", "agua"],
                 "Torre del Reloj", 10.4225, -75.5497, "Caminata histórica por el centro y el barrio Getsemaní."),
    "tayrona": ("Parque Tayrona: Cabo San Juan", "SMR", 9, 220000, 14, 7, 2, 2, ["transporte", "entrada al parque", "guía"],
                "Parque de Los Novios", 11.2422, -74.2108, "Caminata por el bosque seco hasta las playas del Cabo San Juan."),
    "johnny": ("Johnny Cay y Acuario", "ADZ", 6, 120000, 20, 9, 2, 2, ["lancha", "impuesto de ingreso", "careta"],
               "Muelle Casa de la Cultura", 12.5850, -81.6990, "Visita a los cayos con tiempo libre para nadar."),
    "cabo": ("Cabo de la Vela y Punta Gallinas", "RCH", 12, 380000, 12, 5, 2, 3, ["transporte 4x4", "almuerzo", "guía wayuu"],
             "Parque Padilla", 11.5440, -72.9070, "Expedición por el desierto de La Guajira con comunidades wayuu."),
    "comuna13": ("Graffitour Comuna 13", "MDE", 4, 95000, 15, 10, 2, 2, ["guía local", "metro cable"],
                 "Estación San Javier", 6.2566, -75.6131, "Arte urbano, historia y escaleras eléctricas de la Comuna 13."),
}


def salida_id(fecha: datetime) -> str:
    return f"S{fecha:%Y%m%d%H%M}"


def cargar_catalogo(db) -> dict:
    db.ciudades.insert_many([{"_id": i, "nombre": n, "departamento": d} for i, n, d in CIUDADES])
    db.asesores.insert_many([dict(a) for a in ASESORES])

    clientes = []
    for i, nombre in enumerate(NOMBRES_CLIENTES):
        usuario = nombre.lower().split()[0].translate(str.maketrans("áéíóú", "aeiou"))
        doc = {"documento": str(1010200300 + i * 7919), "nombre": nombre,
               "correo": f"{usuario}.{i + 1}@correo.com", "telefono": f"+57 3{random.randint(0, 2)}{random.randint(10000000, 99999999)}",
               "fecha_registro": dia(-random.randint(100, 200), 10)}
        if i % 3 != 2:
            doc["preferencias"] = {"destinos_favoritos": random.sample(["CTG", "SMR", "ADZ", "RCH", "MDE"], 2),
                                   "presupuesto": random.choice([1500000, 2500000, 4000000, 6000000]),
                                   "viaja_con_ninos": random.random() < 0.35}
        clientes.append(doc)
    db.clientes.insert_many(clientes)

    for cod, aer, o, d, n, h, dur, p in VUELOS:
        salida = dia(n, h)
        db.vuelos.insert_one({
            "codigo": cod, "aerolinea": aer,
            "origen": {"iata": o, "nombre": NOMBRE[o]}, "destino": {"iata": d, "nombre": NOMBRE[d]},
            "salida": salida, "llegada": salida + timedelta(minutes=dur),
            "tarifas": [
                {"tipo": "Básica", "precio": p, "equipaje": "Artículo personal", "sillas_totales": 20, "sillas_disponibles": 20},
                {"tipo": "Clásica", "precio": int(round(p * 1.35, -3)), "equipaje": "Maleta de 23 kg", "sillas_totales": 14, "sillas_disponibles": 14},
                {"tipo": "Flexible", "precio": int(round(p * 1.8, -3)), "equipaje": "Maleta de 23 kg + cambios sin costo", "sillas_totales": 6, "sillas_disponibles": 6},
            ]})

    hoteles = {}
    for clave, h in HOTELES.items():
        doc = {"nombre": h["nombre"], "ciudad": {"iata": h["ciudad"], "nombre": NOMBRE[h["ciudad"]]},
               "direccion": h["direccion"], "categoria": h["categoria"], "servicios": h["servicios"],
               "ubicacion": {"type": "Point", "coordinates": [h["lon"], h["lat"]]},
               "tipos_habitacion": [{"tipo": t, "capacidad": c, "precio_noche": p, "total_habitaciones": n}
                                    for t, c, p, n in h["tipos"]]}
        hoteles[clave] = db.hoteles.insert_one(doc).inserted_id
        db.disponibilidad_hotel.insert_many([
            {"hotel_id": hoteles[clave], "tipo": t, "fecha": dia(i), "total": n, "libres": n}
            for t, c, p, n in h["tipos"] for i in range(DIAS_CALENDARIO)])

    tours = {}
    for clave, (nom, ciu, horas, precio, cupos, hora, primero, cada, incluye, punto, lat, lon, desc) in TOURS.items():
        fechas = [dia(n, hora) for n in range(primero, 31, cada)]
        tours[clave] = db.tours.insert_one({
            "nombre": nom, "ciudad": {"iata": ciu, "nombre": NOMBRE[ciu]}, "descripcion": desc,
            "duracion_horas": horas, "incluye": incluye,
            "punto_encuentro": {"nombre": punto, "ubicacion": {"type": "Point", "coordinates": [lon, lat]}},
            "salidas": [{"salida_id": salida_id(f), "fecha": f, "precio": precio,
                         "cupos_totales": cupos, "cupos_disponibles": cupos} for f in fechas],
        }).inserted_id
    return {"hoteles": hoteles, "tours": tours}


def crear_paquetes(db, ids: dict) -> None:
    """Paquete = referencias (para descontar inventario) + copia de nombre/fecha/precio de referencia (para mostrar)."""
    def c_vuelo(cod, tarifa):
        v = db.vuelos.find_one({"codigo": cod})
        t = next(t for t in v["tarifas"] if t["tipo"] == tarifa)
        return {"tipo": "vuelo", "vuelo_id": v["_id"], "vuelo_codigo": cod, "tarifa": tarifa, "fecha": v["salida"],
                "precio_referencia": t["precio"],
                "descripcion": f"Vuelo {cod} {v['origen']['iata']}→{v['destino']['iata']} {v['salida']:%Y-%m-%d %H:%M}"}

    def c_hotel(clave, tipo, desde, noches):
        h = db.hoteles.find_one({"_id": ids["hoteles"][clave]})
        th = next(x for x in h["tipos_habitacion"] if x["tipo"] == tipo)
        return {"tipo": "hotel", "hotel_id": h["_id"], "hotel_nombre": h["nombre"], "tipo_habitacion": tipo,
                "capacidad": th["capacidad"], "fecha_entrada": dia(desde), "noches": noches,
                "precio_referencia": th["precio_noche"],
                "descripcion": f"{noches} noches en {h['nombre']} ({tipo}) desde {dia(desde):%Y-%m-%d}"}

    def c_tour(clave, n):
        t = db.tours.find_one({"_id": ids["tours"][clave]})
        s = next(s for s in t["salidas"] if s["fecha"].date() == dia(n).date())
        return {"tipo": "tour", "tour_id": t["_id"], "tour_nombre": t["nombre"], "salida_id": s["salida_id"],
                "fecha": s["fecha"], "precio_referencia": s["precio"],
                "descripcion": f"Tour {t['nombre']} {s['fecha']:%Y-%m-%d %H:%M}"}

    vig = lambda hasta: {"desde": dia(-120), "hasta": dia(hasta)}
    db.paquetes.insert_many([
        {"codigo": "PKG-CTG-4N", "nombre": "Cartagena 4 noches", "destino": {"iata": "CTG", "nombre": "Cartagena"},
         "descuento_pct": 12, "vigencia": vig(9),
         "componentes": [c_vuelo("AV9403", "Clásica"), c_hotel("murallas", "Doble", 10, 4),
                         c_tour("islas", 12), c_vuelo("AV9404", "Clásica")]},
        {"codigo": "PKG-SMR-3N", "nombre": "Santa Marta y Tayrona 3 noches", "destino": {"iata": "SMR", "nombre": "Santa Marta"},
         "descuento_pct": 10, "vigencia": vig(14),
         "componentes": [c_vuelo("LA4203", "Básica"), c_hotel("rodadero", "Doble", 15, 3),
                         c_tour("tayrona", 16), c_vuelo("LA4204", "Básica")]},
        {"codigo": "PKG-ADZ-5N", "nombre": "San Andrés 5 noches", "destino": {"iata": "ADZ", "nombre": "San Andrés"},
         "descuento_pct": 15, "vigencia": vig(19),
         "componentes": [c_vuelo("AV9601", "Clásica"), c_hotel("posada", "Doble", 20, 5),
                         c_tour("johnny", 22), c_vuelo("AV9602", "Clásica")]},
        {"codigo": "PKG-RCH-4N", "nombre": "La Guajira: Cabo de la Vela 4 noches", "destino": {"iata": "RCH", "nombre": "Riohacha"},
         "descuento_pct": 10, "vigencia": vig(6),
         "componentes": [c_vuelo("AV9701", "Básica"), c_hotel("arena", "Doble", 7, 4),
                         c_tour("cabo", 8), c_vuelo("AV9702", "Básica")]},
    ])


def cargar_reservas(db, ids: dict) -> None:
    def V(cod, tarifa, n):
        return ItemIn(tipo="vuelo", vuelo_codigo=cod, tarifa=tarifa, cantidad=n)

    def H(clave, tipo, desde, noches, n):
        return ItemIn(tipo="hotel", hotel_id=str(ids["hoteles"][clave]), tipo_habitacion=tipo,
                      fecha_entrada=dia(desde).date(), noches=noches, cantidad=n)

    def T(clave, n_dia, n):
        t = db.tours.find_one({"_id": ids["tours"][clave]})
        s = next(s for s in t["salidas"] if s["fecha"].date() == dia(n_dia).date())
        return ItemIn(tipo="tour", tour_id=str(t["_id"]), salida_id=s["salida_id"], cantidad=n)

    def P(cod, n):
        return ItemIn(tipo="paquete", paquete_codigo=cod, cantidad=n)

    plan = [
        (95, 0, "A01", [P("PKG-CTG-4N", 2)], 2, "pagada"),
        (90, 1, "A02", [V("AV9401", "Básica", 1), V("AV9402", "Básica", 1), H("bocagrande", "Sencilla", 3, 3, 1)], 1, "pagada"),
        (86, 2, "A03", [P("PKG-SMR-3N", 4)], 4, "parcial"),
        (80, 3, "A01", [V("LA4201", "Clásica", 2), V("LA4202", "Clásica", 2), H("rodadero", "Doble", 5, 3, 1), T("tayrona", 6, 2)], 2, "cancelada"),
        (76, 4, "A02", [P("PKG-ADZ-5N", 2)], 2, "pagada"),
        (71, 5, "A03", [H("murallas", "Doble", 12, 1, 2)], 4, "pagada"),
        (66, 6, "A01", [V("AV9701", "Básica", 3), V("AV9702", "Básica", 3), H("arena", "Doble", 7, 4, 2)], 3, "pagada"),
        (60, 7, "A02", [P("PKG-RCH-4N", 2)], 2, "parcial"),
        (55, 8, "A03", [V("AV9201", "Flexible", 1), V("AV9202", "Flexible", 1), H("poblado", "Sencilla", 2, 3, 1), T("comuna13", 4, 1)], 1, "pagada"),
        (50, 9, "A01", [P("PKG-CTG-4N", 2)], 2, "pagada"),
        (46, 10, "A02", [V("P57301", "Básica", 2), V("P57302", "Básica", 2), T("murallas", 5, 2)], 2, "cancelada_con_abono"),
        (41, 11, "A03", [P("PKG-ADZ-5N", 3)], 3, "pendiente"),
        (37, 12, "A01", [V("LA4101", "Clásica", 2), V("LA4102", "Clásica", 2), H("bocagrande", "Familiar", 17, 4, 1), T("islas", 18, 2)], 2, "pagada"),
        (32, 13, "A02", [T("johnny", 20, 4), H("posada", "Familiar", 20, 3, 1)], 4, "parcial"),
        (28, 14, "A03", [P("PKG-SMR-3N", 2)], 2, "pagada"),
        (24, 0, "A01", [V("AV9601", "Básica", 2), V("AV9602", "Básica", 2)], 2, "cancelada"),
        (20, 2, "A02", [P("PKG-CTG-4N", 2)], 2, "cancelada"),
        (16, 4, "A03", [V("AV9403", "Flexible", 1), V("AV9404", "Flexible", 1), H("bocagrande", "Doble", 10, 4, 1)], 1, "pagada"),
        (12, 6, "A01", [P("PKG-RCH-4N", 4)], 4, "parcial"),
        (9, 8, "A02", [T("cabo", 11, 2), H("arena", "Sencilla", 10, 2, 2)], 2, "pendiente"),
        (6, 10, "A03", [V("AV9201", "Básica", 2), V("AV9202", "Básica", 2), T("comuna13", 4, 2)], 2, "pagada"),
        (4, 12, "A01", [P("PKG-ADZ-5N", 2)], 2, "parcial"),
        (2, 1, "A02", [V("AV9401", "Clásica", 4), V("AV9402", "Clásica", 4), T("murallas", 5, 4)], 4, "pendiente"),
        (1, 3, "A03", [P("PKG-SMR-3N", 2)], 2, "cancelada"),
        (0, 5, "A01", [V("LA4201", "Básica", 1), V("LA4202", "Básica", 1)], 1, "pendiente"),
    ]
    medios = ["Tarjeta de crédito", "PSE", "Transferencia", "Tarjeta débito", "Efectivo"]
    usuarios = {a["codigo"]: a["usuario"] for a in ASESORES}

    for atras, ic, asesor, items, npax, final in plan:
        cliente = db.clientes.find_one({"nombre": NOMBRES_CLIENTES[ic]})
        pax = [PasajeroIn(nombre=cliente["nombre"], documento=cliente["documento"],
                          fecha_nacimiento=date(random.randint(1965, 2000), random.randint(1, 12), random.randint(1, 28)))]
        for _ in range(npax - 1):
            pax.append(PasajeroIn(nombre=random.choice(OTROS_PASAJEROS), documento=str(random.randint(1000000000, 1099999999)),
                                  fecha_nacimiento=date(random.randint(1960, 2020), random.randint(1, 12), random.randint(1, 28))))
        creada = min(dia(-atras, random.randint(8, 17), random.choice([0, 15, 30, 45])), AHORA)
        r = svc.crear_reserva(db, ReservaCreate(cliente_documento=cliente["documento"], asesor_codigo=asesor,
                                                items=items, pasajeros=pax), fecha_creacion=creada)
        usuario = usuarios[asesor]

        def fecha_despues(d):
            return min(creada + timedelta(days=d, hours=random.randint(0, 5)), AHORA)

        if final in ("pagada", "parcial", "cancelada_con_abono"):
            abono = round(r["total"] * random.choice([0.3, 0.4, 0.5]), -3)
            svc.registrar_pago(db, r["codigo"], PagoCreate(valor=abono, medio=random.choice(medios), usuario=usuario),
                               fecha=fecha_despues(0))
            if final == "pagada":
                svc.registrar_pago(db, r["codigo"], PagoCreate(valor=r["total"] - abono, medio=random.choice(medios),
                                                               usuario=usuario), fecha=fecha_despues(min(atras, 7)))
        if final.startswith("cancelada"):
            svc.cancelar_reserva(db, r["codigo"], CancelacionCreate(usuario=usuario, motivo="El cliente desistió del viaje"),
                                 fecha=fecha_despues(min(atras, 3)))


def verificar_coherencia(db) -> None:
    """Sillas/habitaciones/cupos vendidos (según inventario) == suma de cantidades en reservas activas."""
    from app.services.inventario import agrupar, operaciones_de_items
    vendido: dict = {}
    for r in db.reservas.find({"estado": {"$ne": "Cancelada"}}, {"items": 1}):
        for op in agrupar(operaciones_de_items(r["items"])):
            k = (op["tipo"], op.get("vuelo_id") or op.get("hotel_id") or op.get("tour_id"),
                 op.get("tarifa") or op.get("tipo_habitacion") or op.get("salida_id"), op.get("fecha"))
            vendido[k] = vendido.get(k, 0) + op["cantidad"]
    errores = 0
    for v in db.vuelos.find():
        for t in v["tarifas"]:
            errores += (t["sillas_totales"] - t["sillas_disponibles"]) != vendido.get(("vuelo", v["_id"], t["tipo"], None), 0)
    for d in db.disponibilidad_hotel.find():
        errores += (d["total"] - d["libres"]) != vendido.get(("hotel", d["hotel_id"], d["tipo"], d["fecha"]), 0)
    for t in db.tours.find():
        for s in t["salidas"]:
            errores += (s["cupos_totales"] - s["cupos_disponibles"]) != vendido.get(("tour", t["_id"], s["salida_id"], None), 0)
    print(f"Coherencia inventario vs. reservas: {'OK' if errores == 0 else f'{errores} diferencias'}")
    if errores:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=MONGO_DB)
    args = ap.parse_args()
    db = get_database(args.db)
    db.client.drop_database(args.db)
    crear_esquema(db)
    ids = cargar_catalogo(db)
    crear_paquetes(db, ids)
    cargar_reservas(db, ids)

    print(f"Base '{args.db}' cargada:")
    for c in ["ciudades", "asesores", "clientes", "vuelos", "hoteles", "disponibilidad_hotel", "tours", "paquetes", "reservas"]:
        print(f"  {c:<22}{db[c].count_documents({})}")
    print("  reservas por estado:", {e["_id"]: e["n"] for e in db.reservas.aggregate(
        [{"$group": {"_id": "$estado", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}}])})
    verificar_coherencia(db)
    print("\nB1 ventas por mes:")
    for f in db.reservas.aggregate(reportes.pipeline_ventas_por_mes()):
        print(f"  {f['periodo']}  reservas={f['reservas']:>2}  vendido=${f['total_vendido']:>12,.0f}")


if __name__ == "__main__":
    main()
