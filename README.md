# Brújula Viajes — MongoDB + FastAPI + Streamlit

Proyecto final de Ingeniería de Datos (Universidad del Rosario). Sistema de una agencia que vende
tiquetes, noches de hotel, tours y paquetes. Muestra la disponibilidad real, no vende lo que no tiene
y reporta ventas por mes, destinos y ocupación de vuelos.

```
Streamlit (frontend)  --HTTP/JSON-->  FastAPI (DTO Pydantic)  --PyMongo-->  MongoDB
```

Streamlit **nunca** se conecta a MongoDB: toda operación pasa por la API.

## Estructura

```
brujula-viajes/
├── api/
│   ├── app/
│   │   ├── main.py            # FastAPI, routers y manejo de errores (409/422/404)
│   │   ├── database.py        # MongoClient, base y dependencia get_db (lee .env)
│   │   ├── setup_db.py        # validadores $jsonSchema e índices (se aplican al iniciar)
│   │   ├── schemas.py         # DTO Pydantic (XxxCreate / XxxResponse); _id sale como texto
│   │   ├── reportes.py        # pipelines de agregación B1, B2, B3
│   │   ├── utils.py
│   │   ├── services/
│   │   │   ├── inventario.py  # verificación, descuento con $inc condicional y devolución
│   │   │   └── reservas.py    # crear reserva, pagos, cancelación, precios vigentes
│   │   └── routers/           # clientes (+asesores, ciudades), vuelos, hoteles, tours, paquetes, reservas, reportes
│   └── requirements.txt
├── frontend/
│   ├── app.py                 # Buscar y reservar · Reservas · Catálogo y clientes · Reportes
│   └── requirements.txt
├── scripts/
│   ├── seed.py                # datos de prueba sobre base vacía + verificación de coherencia
│   ├── evidencias.py          # genera evidencias/evidencias.md llamando a la API
│   └── validador_mongosh.js   # evidencia del validador desde mongosh
├── evidencias/evidencias.md   # salida de ejemplo de scripts/evidencias.py
├── docker-compose.yml         # MongoDB 7 local (opcional)
└── .env.example
```

## Cómo levantar todo

Requisitos: Python 3.11 o superior y MongoDB 6.0 o superior (local, Docker o Atlas).

```bash
# 0) MongoDB (elija una opción)
docker compose up -d                      # local con Docker
# ...o use su instalación local, o una cadena de Atlas en MONGO_URI

# 1) Entorno y dependencias
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r api/requirements.txt -r frontend/requirements.txt
cp .env.example .env                      # ajuste MONGO_URI si usa Atlas

# 2) Datos de prueba (BORRA y recrea la base MONGO_DB)
python scripts/seed.py

# 3) API  ->  http://localhost:8000/docs
cd api && uvicorn app.main:app --reload --port 8000

# 4) Frontend (otra terminal)  ->  http://localhost:8501
cd frontend && streamlit run app.py

# 5) Evidencias (opcional, con la API corriendo)
python scripts/evidencias.py
mongosh "mongodb://localhost:27017/brujula_viajes" scripts/validador_mongosh.js
```

El catálogo de prueba usa fechas **relativas al día en que se ejecuta el seed** (vuelos en los próximos
30 días, calendario de hoteles de 45 noches, salidas de tours cada 2–3 días). Por eso siempre hay
disponibilidad futura; si pasan varias semanas, vuelva a ejecutar `seed.py`.

## Datos de prueba

| Colección | Documentos |
|---|---|
| ciudades | 6 (BOG, CTG, SMR, MDE, ADZ, RCH) |
| vuelos | 20 (ida y regreso por ruta, 3 tarifas cada uno) |
| hoteles | 6 en 5 ciudades + 675 documentos de `disponibilidad_hotel` (hotel × tipo × noche) |
| tours | 6, con varias salidas programadas |
| paquetes | 4 vigentes |
| clientes / asesores | 15 / 3 |
| reservas | 25 en los 3 estados, de agosto a noviembre (fechas relativas) |

Las reservas se crean con **la misma lógica de la API**, así que el inventario descontado coincide
con lo vendido. Al final, `seed.py` verifica esa coherencia (sillas, habitaciones por noche y cupos)
e imprime `Coherencia inventario vs. reservas: OK`.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET, POST | `/clientes/` · `GET /clientes/{documento}` | Listar, registrar y consultar clientes |
| GET, POST | `/asesores/`, `/ciudades/` | Catálogos de apoyo |
| GET, POST | `/vuelos/?origen=&destino=&fecha=` | Catálogo y búsqueda de vuelos |
| GET, POST | `/hoteles/?ciudad=&entrada=&noches=` | Hoteles con habitaciones libres **todas** las noches pedidas |
| GET | `/hoteles/{id}/disponibilidad` | Calendario por noche |
| GET, POST | `/tours/?ciudad=&fecha=` | Tours y salidas futuras |
| GET, POST | `/paquetes/?destino=&personas=` | Paquetes con precio actual y si **todos** sus componentes tienen cupo |
| GET, POST | `/reservas/` | Listar (filtros: estado, cliente, asesor) y crear |
| GET | `/reservas/{codigo}` | Detalle con ítems, pasajeros, pagos e historial |
| POST | `/reservas/{codigo}/pagos` | Registrar un pago (pasa a *Pagada* al cubrir el total) |
| POST | `/reservas/{codigo}/cancelar` | Cancelar y devolver inventario |
| GET | `/reportes/ventas-por-mes` | B1 |
| GET | `/reportes/destinos-mas-vendidos` | B2 |
| GET | `/reportes/ocupacion-vuelos` | B3 |

Códigos HTTP: **201** al crear · **404** si no existe · **409** sin cupo o regla incumplida (pago en
reserva cancelada, pago mayor al saldo, duplicados) · **422** datos inválidos (Pydantic o validador de
MongoDB) · **503** sin conexión a la base.

## Reglas implementadas

- **Validadores `$jsonSchema`** en todas las colecciones (obligatorios: vuelos, hoteles, reservas):
  campos requeridos, fechas `date`, IATA con patrón `^[A-Z]{3}$`, estados permitidos, mínimos de cero
  y tamaño máximo de los arreglos.
- **Índices únicos**: `clientes.documento`, `vuelos.codigo`, `reservas.codigo` (además de
  `paquetes.codigo`, `asesores.codigo/usuario` y `disponibilidad_hotel(hotel_id, tipo, fecha)`).
- **Disponibilidad**: se verifica antes de crear (409 con el detalle: vuelo y tarifa, hotel, tipo y
  noche, o salida del tour) y se descuenta con `$inc` **condicional** (`disponible >= cantidad` en el
  filtro). Si una operación falla por concurrencia, se devuelven las ya aplicadas (compensación).
  Al cancelar se devuelve todo con `$inc`.
- **Precios**: cada ítem guarda el precio vigente al reservar. Paquete = suma de componentes − descuento.
  Total = suma de ítems.
- **Pagos e historial**: `$push` del pago; al cubrir el total, `$set estado: "Pagada"` y `$push` al
  historial (estado anterior, nuevo, fecha y usuario) en la misma operación.
