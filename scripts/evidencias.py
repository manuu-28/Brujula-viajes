import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from pymongo.errors import DuplicateKeyError, WriteError

from app.database import get_database

API = os.getenv("API_URL", "http://localhost:8000")
SALIDA = Path(__file__).resolve().parents[1] / "evidencias" / "evidencias.md"
db = get_database()
md: list[str] = [f"# Evidencias — Brújula Viajes\n\nGeneradas el {datetime.now():%Y-%m-%d %H:%M} contra `{API}`.\n"]


def bloque(titulo: str, contenido, lenguaje: str = "json") -> None:
    if not isinstance(contenido, str):
        contenido = json.dumps(contenido, ensure_ascii=False, indent=2, default=str)
    md.append(f"\n### {titulo}\n\n```{lenguaje}\n{contenido}\n```\n")


def llamar(metodo: str, ruta: str, **kw):
    r = requests.request(metodo, API + ruta, timeout=30, **kw)
    return r.status_code, r.json()


def sillas(codigo: str, tarifa: str) -> int:
    v = db.vuelos.find_one({"codigo": codigo})
    return next(t["sillas_disponibles"] for t in v["tarifas"] if t["tipo"] == tarifa)


md.append("\n## 1. Documentos rechazados por el validador ($jsonSchema)\n")
md.append("Inserción directa con PyMongo (equivale a `db.vuelos.insertOne(...)` en mongosh; la validación la hace el servidor).\n")
vuelo_malo = {"codigo": "BV1234", "aerolinea": "Avianca", "origen": {"iata": "Bogotá", "nombre": "Bogotá"},
              "destino": {"iata": "CTG", "nombre": "Cartagena"}, "salida": datetime(2026, 12, 1, 7),
              "llegada": datetime(2026, 12, 1, 8, 25),
              "tarifas": [{"tipo": "Básica", "precio": 250000, "equipaje": "Personal", "sillas_totales": 20, "sillas_disponibles": 20}]}
for nombre, col, doc in [
    ("Vuelo con origen \"Bogotá\" en lugar de \"BOG\"", "vuelos", vuelo_malo),
    ("Vuelo con precio negativo y fecha como texto", "vuelos",
     {**vuelo_malo, "origen": {"iata": "BOG", "nombre": "Bogotá"}, "salida": "2026-12-01 07:00",
      "tarifas": [{**vuelo_malo["tarifas"][0], "precio": -100}]}),
    ("Reserva con estado \"Reservada\"", "reservas", {**db.reservas.find_one({}, {"_id": 0}), "codigo": "RSV-999999", "estado": "Reservada"}),
]:
    try:
        db[col].insert_one(doc)
        bloque(nombre, "¡Se insertó! (no debería)", "text")
    except WriteError as e:
        reglas = json.dumps(e.details.get("errInfo", {}).get("details", {}).get("schemaRulesNotSatisfied", []),
                            ensure_ascii=False, default=str)
        bloque(nombre, f"WriteError code={e.code}: {e.details.get('errmsg')}\nschemaRulesNotSatisfied: {reglas[:700]}", "text")

md.append("\n## 2. Índices únicos\n")
cliente = db.clientes.find_one()
try:
    db.clientes.insert_one({k: v for k, v in cliente.items() if k != "_id"})
except DuplicateKeyError as e:
    bloque("Cliente con documento repetido (directo en MongoDB)", f"DuplicateKeyError E11000: {e.details.get('keyValue')}", "text")
status, body = llamar("POST", "/clientes/", json={"documento": cliente["documento"], "nombre": "Duplicado",
                                                  "correo": "dup@correo.com", "telefono": "3000000000"})
bloque(f"POST /clientes/ con documento repetido → HTTP {status}", body)
bloque("Índices de la colección reservas", db.reservas.index_information())

md.append("\n## 3. Reserva rechazada por falta de cupo (HTTP 409)\n")
_, paquete = llamar("GET", "/paquetes/PKG-CTG-4N", params={"personas": 4})
bloque("Cotización del paquete Cartagena 4 noches para 4 personas", paquete["cotizacion"])
total_antes = db.reservas.count_documents({})
pedido = {"cliente_documento": cliente["documento"], "asesor_codigo": "A01",
          "items": [{"tipo": "paquete", "paquete_codigo": "PKG-CTG-4N", "cantidad": 4}],
          "pasajeros": [{"nombre": f"Pasajero {i}", "documento": f"10000{i}", "fecha_nacimiento": "1990-05-10"} for i in range(4)]}
status, body = llamar("POST", "/reservas/", json=pedido)
bloque(f"POST /reservas/ paquete para 4 personas → HTTP {status}", body)
md.append(f"\nReservas antes: {total_antes} · después: {db.reservas.count_documents({})} (no se creó nada; "
          f"tampoco se descontaron las sillas del vuelo AV9403 Clásica: {sillas('AV9403', 'Clásica')}).\n")

vuelo_lleno = {"cliente_documento": cliente["documento"], "asesor_codigo": "A02",
               "items": [{"tipo": "vuelo", "vuelo_codigo": "AV9201", "tarifa": "Flexible", "cantidad": 7}],
               "pasajeros": [{"nombre": "Ana", "documento": "123456", "fecha_nacimiento": "1990-01-01"}]}
status, body = llamar("POST", "/reservas/", json=vuelo_lleno)
bloque(f"POST /reservas/ con 7 sillas Flexible (solo hay {sillas('AV9201', 'Flexible')}) → HTTP {status}", body)

md.append("\n## 4. Datos inválidos (HTTP 422)\n")
status, body = llamar("POST", "/reservas/", json={**vuelo_lleno, "items": [{"tipo": "vuelo", "vuelo_codigo": "AV9201", "cantidad": 0}]})
bloque(f"POST /reservas/ con cantidad 0 y sin tarifa → HTTP {status}", body)

md.append("\n## 5. Pagos e historial: la reserva pasa a Pagada\n")
nueva = {"cliente_documento": cliente["documento"], "asesor_codigo": "A03",
         "items": [{"tipo": "vuelo", "vuelo_codigo": "LA4101", "tarifa": "Básica", "cantidad": 2},
                   {"tipo": "vuelo", "vuelo_codigo": "LA4102", "tarifa": "Básica", "cantidad": 2},
                   {"tipo": "tour", "tour_id": str(db.tours.find_one({"ciudad.iata": "CTG", "nombre": {"$regex": "Islas"}})["_id"]),
                    "salida_id": db.tours.find_one({"nombre": {"$regex": "Islas"}})["salidas"][-1]["salida_id"], "cantidad": 2}],
         "pasajeros": [{"nombre": cliente["nombre"], "documento": cliente["documento"], "fecha_nacimiento": "1988-03-14"},
                       {"nombre": "Acompañante", "documento": "52123456", "fecha_nacimiento": "1990-07-22"}]}
status, r = llamar("POST", "/reservas/", json=nueva)
codigo = r["codigo"]
bloque(f"POST /reservas/ → HTTP {status}", {k: r[k] for k in ["codigo", "estado", "total", "total_pagado", "saldo"]}
       | {"items": [(i["descripcion"], i["cantidad"], i["precio_unitario"], i["subtotal"]) for i in r["items"]]})
abono = round(r["total"] * 0.4, -3)
status, r = llamar("POST", f"/reservas/{codigo}/pagos", json={"valor": abono, "medio": "PSE", "usuario": "crojas"})
bloque(f"Abono de {abono:,.0f} → HTTP {status}", {k: r[k] for k in ["estado", "total", "total_pagado", "saldo"]})
status, body = llamar("POST", f"/reservas/{codigo}/pagos", json={"valor": r["saldo"] + 1000, "medio": "PSE", "usuario": "crojas"})
bloque(f"Pago mayor al saldo → HTTP {status}", body)
status, r = llamar("POST", f"/reservas/{codigo}/pagos", json={"valor": r["saldo"], "medio": "Tarjeta de crédito", "usuario": "crojas"})
bloque(f"Pago del saldo → HTTP {status}", {k: r[k] for k in ["estado", "total", "total_pagado", "saldo", "pagos", "historial"]})

md.append("\n## 6. Cancelación que devuelve el inventario\n")
antes = {"LA4101 Básica": sillas("LA4101", "Básica"), "LA4102 Básica": sillas("LA4102", "Básica")}
status, r = llamar("POST", f"/reservas/{codigo}/cancelar", json={"usuario": "crojas", "motivo": "Cambio de planes"})
despues = {"LA4101 Básica": sillas("LA4101", "Básica"), "LA4102 Básica": sillas("LA4102", "Básica")}
bloque(f"POST /reservas/{codigo}/cancelar → HTTP {status}", {"estado": r["estado"], "historial": r["historial"]})
bloque("Sillas disponibles antes y después de cancelar", {"antes": antes, "despues": despues})
status, body = llamar("POST", f"/reservas/{codigo}/pagos", json={"valor": 1000, "medio": "PSE", "usuario": "crojas"})
bloque(f"Pago sobre la reserva cancelada → HTTP {status}", body)
status, body = llamar("POST", f"/reservas/{codigo}/cancelar", json={"usuario": "crojas"})
bloque(f"Cancelar dos veces → HTTP {status}", body)
status, body = llamar("GET", "/reservas/RSV-000000")
bloque(f"Reserva inexistente → HTTP {status}", body)

md.append("\n## 7. Reportes B1 a B3 (pipelines de agregación)\n")
for titulo, ruta in [("B1. Ventas por mes", "/reportes/ventas-por-mes"),
                     ("B2. Destinos más vendidos", "/reportes/destinos-mas-vendidos"),
                     ("B3. Ocupación de vuelos (primeros 8)", "/reportes/ocupacion-vuelos")]:
    status, body = llamar("GET", ruta)
    bloque(f"GET {ruta} → HTTP {status} — {titulo}", body[:8])

SALIDA.write_text("".join(md), encoding="utf-8")
print(f"Evidencias escritas en {SALIDA}")
