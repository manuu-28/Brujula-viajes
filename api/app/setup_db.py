"""Validadores $jsonSchema e índices de todas las colecciones."""
from pymongo import ASCENDING, DESCENDING, GEOSPHERE
from pymongo.database import Database

NUM = ["int", "long", "double", "decimal"]
IATA = {"bsonType": "string", "pattern": "^[A-Z]{3}$"}
CIUDAD_REF = {
    "bsonType": "object",
    "required": ["iata", "nombre"],
    "properties": {"iata": IATA, "nombre": {"bsonType": "string"}},
}
PUNTO_GEO = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"enum": ["Point"]},
        "coordinates": {"bsonType": "array", "minItems": 2, "maxItems": 2, "items": {"bsonType": NUM}},
    },
}
ESTADOS_RESERVA = ["Pendiente", "Pagada", "Cancelada"]
TIPOS_TARIFA = ["Básica", "Clásica", "Flexible"]
TIPOS_HABITACION = ["Sencilla", "Doble", "Familiar", "Suite"]
MEDIOS_PAGO = ["Efectivo", "Tarjeta de crédito", "Tarjeta débito", "PSE", "Transferencia"]

VALIDADORES = {
    "ciudades": {
        "bsonType": "object",
        "required": ["_id", "nombre", "departamento"],
        "properties": {"_id": IATA, "nombre": {"bsonType": "string"}, "departamento": {"bsonType": "string"}},
    },
    "asesores": {
        "bsonType": "object",
        "required": ["codigo", "nombre", "correo", "usuario", "activo"],
        "properties": {
            "codigo": {"bsonType": "string"},
            "nombre": {"bsonType": "string"},
            "correo": {"bsonType": "string", "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"},
            "usuario": {"bsonType": "string"},
            "activo": {"bsonType": "bool"},
        },
    },
    "clientes": {
        "bsonType": "object",
        "required": ["documento", "nombre", "correo", "telefono", "fecha_registro"],
        "properties": {
            "documento": {"bsonType": "string", "minLength": 5},
            "nombre": {"bsonType": "string", "minLength": 2},
            "correo": {"bsonType": "string", "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"},
            "telefono": {"bsonType": "string"},
            "fecha_registro": {"bsonType": "date"},
            "preferencias": {
                "bsonType": "object",
                "properties": {
                    "destinos_favoritos": {"bsonType": "array", "maxItems": 10, "items": IATA},
                    "presupuesto": {"bsonType": NUM, "minimum": 0},
                    "viaja_con_ninos": {"bsonType": "bool"},
                },
            },
        },
    },
    "vuelos": {
        "bsonType": "object",
        "required": ["codigo", "aerolinea", "origen", "destino", "salida", "llegada", "tarifas"],
        "properties": {
            "codigo": {"bsonType": "string", "pattern": "^[A-Z0-9]{2}[0-9]{3,4}$"},
            "aerolinea": {"bsonType": "string"},
            "origen": CIUDAD_REF,
            "destino": CIUDAD_REF,
            "salida": {"bsonType": "date"},
            "llegada": {"bsonType": "date"},
            "tarifas": {
                "bsonType": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "bsonType": "object",
                    "required": ["tipo", "precio", "equipaje", "sillas_totales", "sillas_disponibles"],
                    "properties": {
                        "tipo": {"enum": TIPOS_TARIFA},
                        "precio": {"bsonType": NUM, "minimum": 0},
                        "equipaje": {"bsonType": "string"},
                        "sillas_totales": {"bsonType": NUM, "minimum": 0},
                        "sillas_disponibles": {"bsonType": NUM, "minimum": 0},
                    },
                },
            },
        },
    },
    "hoteles": {
        "bsonType": "object",
        "required": ["nombre", "ciudad", "direccion", "categoria", "servicios", "ubicacion", "tipos_habitacion"],
        "properties": {
            "nombre": {"bsonType": "string"},
            "ciudad": CIUDAD_REF,
            "direccion": {"bsonType": "string"},
            "categoria": {"bsonType": "int", "minimum": 1, "maximum": 5},
            "servicios": {"bsonType": "array", "items": {"bsonType": "string"}},
            "ubicacion": PUNTO_GEO,
            "tipos_habitacion": {
                "bsonType": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "bsonType": "object",
                    "required": ["tipo", "capacidad", "precio_noche", "total_habitaciones"],
                    "properties": {
                        "tipo": {"enum": TIPOS_HABITACION},
                        "capacidad": {"bsonType": "int", "minimum": 1},
                        "precio_noche": {"bsonType": NUM, "minimum": 0},
                        "total_habitaciones": {"bsonType": NUM, "minimum": 0},
                    },
                },
            },
        },
    },
    "disponibilidad_hotel": {
        "bsonType": "object",
        "required": ["hotel_id", "tipo", "fecha", "total", "libres"],
        "properties": {
            "hotel_id": {"bsonType": "objectId"},
            "tipo": {"enum": TIPOS_HABITACION},
            "fecha": {"bsonType": "date"},
            "total": {"bsonType": NUM, "minimum": 0},
            "libres": {"bsonType": NUM, "minimum": 0},
        },
    },
    "tours": {
        "bsonType": "object",
        "required": ["nombre", "ciudad", "descripcion", "duracion_horas", "incluye", "punto_encuentro", "salidas"],
        "properties": {
            "nombre": {"bsonType": "string"},
            "ciudad": CIUDAD_REF,
            "duracion_horas": {"bsonType": NUM, "minimum": 0},
            "incluye": {"bsonType": "array", "items": {"bsonType": "string"}},
            "punto_encuentro": {
                "bsonType": "object",
                "required": ["nombre", "ubicacion"],
                "properties": {"nombre": {"bsonType": "string"}, "ubicacion": PUNTO_GEO},
            },
            "salidas": {
                "bsonType": "array",
                "maxItems": 60,
                "items": {
                    "bsonType": "object",
                    "required": ["salida_id", "fecha", "precio", "cupos_totales", "cupos_disponibles"],
                    "properties": {
                        "salida_id": {"bsonType": "string"},
                        "fecha": {"bsonType": "date"},
                        "precio": {"bsonType": NUM, "minimum": 0},
                        "cupos_totales": {"bsonType": NUM, "minimum": 0},
                        "cupos_disponibles": {"bsonType": NUM, "minimum": 0},
                    },
                },
            },
        },
    },
    "paquetes": {
        "bsonType": "object",
        "required": ["codigo", "nombre", "destino", "componentes", "descuento_pct", "vigencia"],
        "properties": {
            "codigo": {"bsonType": "string"},
            "nombre": {"bsonType": "string"},
            "destino": CIUDAD_REF,
            "descuento_pct": {"bsonType": NUM, "minimum": 0, "maximum": 100},
            "vigencia": {
                "bsonType": "object",
                "required": ["desde", "hasta"],
                "properties": {"desde": {"bsonType": "date"}, "hasta": {"bsonType": "date"}},
            },
            "componentes": {
                "bsonType": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": {
                    "bsonType": "object",
                    "required": ["tipo", "descripcion"],
                    "properties": {"tipo": {"enum": ["vuelo", "hotel", "tour"]}},
                },
            },
        },
    },
    "reservas": {
        "bsonType": "object",
        "required": [
            "codigo", "cliente", "asesor", "fecha_creacion", "estado",
            "items", "pasajeros", "total", "total_pagado", "pagos", "historial",
        ],
        "properties": {
            "codigo": {"bsonType": "string", "pattern": "^RSV-[0-9]{6}$"},
            "cliente": {
                "bsonType": "object",
                "required": ["cliente_id", "documento", "nombre"],
                "properties": {"cliente_id": {"bsonType": "objectId"}, "documento": {"bsonType": "string"}},
            },
            "asesor": {
                "bsonType": "object",
                "required": ["asesor_id", "codigo", "nombre"],
                "properties": {"asesor_id": {"bsonType": "objectId"}},
            },
            "fecha_creacion": {"bsonType": "date"},
            "estado": {"enum": ESTADOS_RESERVA},
            "total": {"bsonType": NUM, "minimum": 0},
            "total_pagado": {"bsonType": NUM, "minimum": 0},
            "items": {
                "bsonType": "array",
                "minItems": 1,
                "maxItems": 30,
                "items": {
                    "bsonType": "object",
                    "required": ["tipo", "descripcion", "destino", "cantidad", "precio_unitario", "subtotal"],
                    "properties": {
                        "tipo": {"enum": ["vuelo", "hotel", "tour", "paquete"]},
                        "destino": CIUDAD_REF,
                        "cantidad": {"bsonType": NUM, "minimum": 1},
                        "precio_unitario": {"bsonType": NUM, "minimum": 0},
                        "subtotal": {"bsonType": NUM, "minimum": 0},
                    },
                },
            },
            "pasajeros": {
                "bsonType": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {
                    "bsonType": "object",
                    "required": ["nombre", "documento", "fecha_nacimiento"],
                    "properties": {
                        "nombre": {"bsonType": "string"},
                        "documento": {"bsonType": "string"},
                        "fecha_nacimiento": {"bsonType": "date"},
                    },
                },
            },
            "pagos": {
                "bsonType": "array",
                "maxItems": 24,
                "items": {
                    "bsonType": "object",
                    "required": ["fecha", "valor", "medio", "usuario"],
                    "properties": {
                        "fecha": {"bsonType": "date"},
                        "valor": {"bsonType": NUM, "minimum": 0},
                        "medio": {"enum": MEDIOS_PAGO},
                        "usuario": {"bsonType": "string"},
                    },
                },
            },
            "historial": {
                "bsonType": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {
                    "bsonType": "object",
                    "required": ["fecha", "estado_anterior", "estado_nuevo", "usuario"],
                    "properties": {
                        "fecha": {"bsonType": "date"},
                        "estado_anterior": {"enum": ESTADOS_RESERVA + [None]},
                        "estado_nuevo": {"enum": ESTADOS_RESERVA},
                        "usuario": {"bsonType": "string"},
                    },
                },
            },
        },
    },
}

INDICES = {
    "asesores": [([("codigo", ASCENDING)], {"unique": True}), ([("usuario", ASCENDING)], {"unique": True})],
    "clientes": [([("documento", ASCENDING)], {"unique": True, "name": "ux_documento"}), ([("correo", ASCENDING)], {})],
    "vuelos": [
        ([("codigo", ASCENDING)], {"unique": True, "name": "ux_codigo_vuelo"}),
        ([("origen.iata", ASCENDING), ("destino.iata", ASCENDING), ("salida", ASCENDING)], {}),
    ],
    "hoteles": [([("ciudad.iata", ASCENDING)], {}), ([("ubicacion", GEOSPHERE)], {})],
    "disponibilidad_hotel": [
        ([("hotel_id", ASCENDING), ("tipo", ASCENDING), ("fecha", ASCENDING)], {"unique": True}),
    ],
    "tours": [
        ([("ciudad.iata", ASCENDING), ("salidas.fecha", ASCENDING)], {}),
        ([("punto_encuentro.ubicacion", GEOSPHERE)], {}),
    ],
    "paquetes": [([("codigo", ASCENDING)], {"unique": True}), ([("destino.iata", ASCENDING), ("vigencia.hasta", ASCENDING)], {})],
    "reservas": [
        ([("codigo", ASCENDING)], {"unique": True, "name": "ux_codigo_reserva"}),
        ([("estado", ASCENDING), ("fecha_creacion", DESCENDING)], {}),
        ([("cliente.cliente_id", ASCENDING), ("fecha_creacion", DESCENDING)], {}),
        ([("asesor.asesor_id", ASCENDING), ("fecha_creacion", DESCENDING)], {}),
    ],
}


def crear_esquema(db: Database) -> None:
    existentes = set(db.list_collection_names())
    for nombre, schema in VALIDADORES.items():
        opciones = {"validator": {"$jsonSchema": schema}, "validationLevel": "strict", "validationAction": "error"}
        if nombre in existentes:
            db.command({"collMod": nombre, **opciones})
        else:
            db.create_collection(nombre, **opciones)
    if "contadores" not in existentes:
        db.create_collection("contadores")
    for nombre, indices in INDICES.items():
        for claves, opciones in indices:
            db[nombre].create_index(claves, **opciones)
