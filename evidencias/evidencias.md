# Evidencias — Brújula Viajes

Generadas el 2026-11-06 09:12 contra `http://localhost:8000`.

## 1. Documentos rechazados por el validador ($jsonSchema)
Inserción directa con PyMongo (equivale a `db.vuelos.insertOne(...)` en mongosh; la validación la hace el servidor).

### Vuelo con origen "Bogotá" en lugar de "BOG"

```text
WriteError code=121: Document failed validation
schemaRulesNotSatisfied: [{"operatorName": "properties", "propertiesNotSatisfied": [{"propertyName": "origen", "details": [{"operatorName": "properties", "propertiesNotSatisfied": [{"propertyName": "iata", "details": [{"operatorName": "pattern", "specifiedAs": {"pattern": "^[A-Z]{3}$"}, "reason": "regular expression did not match", "consideredValue": "Bogotá"}]}]}]}]}]
```

### Vuelo con precio negativo y fecha como texto

```text
WriteError code=121: Document failed validation
schemaRulesNotSatisfied: [{"operatorName": "properties", "propertiesNotSatisfied": [{"propertyName": "salida", "details": [{"operatorName": "bsonType", "specifiedAs": {"bsonType": "date"}, "reason": "type did not match", "consideredValue": "2026-12-01 07:00", "consideredType": "string"}]}, {"propertyName": "tarifas", "details": [{"operatorName": "items", "reason": "At least one item did not match the sub-schema", "itemIndex": 0, "details": [{"operatorName": "properties", "propertiesNotSatisfied": [{"propertyName": "precio", "details": [{"operatorName": "minimum", "specifiedAs": {"minimum": 0}, "reason": "comparison failed", "consideredValue": -100}]}]}]}]}]}]
```

### Reserva con estado "Reservada"

```text
WriteError code=121: Document failed validation
schemaRulesNotSatisfied: [{"operatorName": "properties", "propertiesNotSatisfied": [{"propertyName": "estado", "details": [{"operatorName": "enum", "specifiedAs": {"enum": ["Pendiente", "Pagada", "Cancelada"]}, "reason": "value was not found in enum", "consideredValue": "Reservada"}]}]}]
```

## 2. Índices únicos

### Cliente con documento repetido (directo en MongoDB)

```text
DuplicateKeyError E11000: {'documento': '1010200300'}
```

### POST /clientes/ con documento repetido → HTTP 409

```json
{
  "detail": "Ya existe un cliente con documento 1010200300"
}
```

### Índices de la colección reservas

```json
{
  "_id_": {
    "v": 2,
    "key": [
      [
        "_id",
        1
      ]
    ]
  },
  "ux_codigo_reserva": {
    "v": 2,
    "key": [
      [
        "codigo",
        1
      ]
    ],
    "unique": true
  },
  "estado_1_fecha_creacion_-1": {
    "v": 2,
    "key": [
      [
        "estado",
        1
      ],
      [
        "fecha_creacion",
        -1
      ]
    ]
  },
  "cliente.cliente_id_1_fecha_creacion_-1": {
    "v": 2,
    "key": [
      [
        "cliente.cliente_id",
        1
      ],
      [
        "fecha_creacion",
        -1
      ]
    ]
  },
  "asesor.asesor_id_1_fecha_creacion_-1": {
    "v": 2,
    "key": [
      [
        "asesor.asesor_id",
        1
      ],
      [
        "fecha_creacion",
        -1
      ]
    ]
  }
}
```

## 3. Reserva rechazada por falta de cupo (HTTP 409)

### Cotización del paquete Cartagena 4 noches para 4 personas

```json
{
  "personas": 4,
  "disponible": false,
  "motivo": "Sin disponibilidad: Hotel Murallas Coloniales, habitación Doble, noche 2026-11-18 (libres 1, se piden 2)"
}
```

### POST /reservas/ paquete para 4 personas → HTTP 409

```json
{
  "detail": "Sin disponibilidad: Hotel Murallas Coloniales, habitación Doble, noche 2026-11-18 (libres 1, se piden 2)"
}
```

Reservas antes: 25 · después: 25 (no se creó nada; tampoco se descontaron las sillas del vuelo AV9403 Clásica: 10).

### POST /reservas/ con 7 sillas Flexible (solo hay 5) → HTTP 409

```json
{
  "detail": "Sin disponibilidad: vuelo AV9201, tarifa Flexible (quedan 5 sillas, se piden 7)"
}
```

## 4. Datos inválidos (HTTP 422)

### POST /reservas/ con cantidad 0 y sin tarifa → HTTP 422

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": [
        "body",
        "items",
        0,
        "cantidad"
      ],
      "msg": "Input should be greater than or equal to 1",
      "input": 0,
      "ctx": {
        "ge": 1
      }
    }
  ]
}
```

## 5. Pagos e historial: la reserva pasa a Pagada

### POST /reservas/ → HTTP 201

```json
{
  "codigo": "RSV-000026",
  "estado": "Pendiente",
  "total": 1576000.0,
  "total_pagado": 0.0,
  "saldo": 1576000,
  "items": [
    [
      "Vuelo LA4101 BOG→CTG 2026-11-23 09:00 · Básica",
      2,
      259000,
      518000
    ],
    [
      "Vuelo LA4102 CTG→BOG 2026-11-27 20:00 · Básica",
      2,
      269000,
      538000
    ],
    [
      "Tour Islas del Rosario en lancha · 2026-12-06 08:00",
      2,
      260000,
      520000
    ]
  ]
}
```

### Abono de 630,000 → HTTP 201

```json
{
  "estado": "Pendiente",
  "total": 1576000.0,
  "total_pagado": 630000.0,
  "saldo": 946000
}
```

### Pago mayor al saldo → HTTP 409

```json
{
  "detail": "El pago (947,000) supera el saldo pendiente (946,000)"
}
```

### Pago del saldo → HTTP 201

```json
{
  "estado": "Pagada",
  "total": 1576000.0,
  "total_pagado": 1576000.0,
  "saldo": 0,
  "pagos": [
    {
      "fecha": "2026-11-06T14:12:54",
      "valor": 630000,
      "medio": "PSE",
      "usuario": "crojas"
    },
    {
      "fecha": "2026-11-06T14:12:54",
      "valor": 946000,
      "medio": "Tarjeta de crédito",
      "usuario": "crojas"
    }
  ],
  "historial": [
    {
      "fecha": "2026-11-06T14:12:54",
      "estado_anterior": null,
      "estado_nuevo": "Pendiente",
      "usuario": "crojas",
      "nota": "Reserva creada; cupos apartados"
    },
    {
      "fecha": "2026-11-06T14:12:54",
      "estado_anterior": "Pendiente",
      "estado_nuevo": "Pagada",
      "usuario": "crojas",
      "nota": "Pagos cubren el total (2 pago(s))"
    }
  ]
}
```

## 6. Cancelación que devuelve el inventario

### POST /reservas/RSV-000026/cancelar → HTTP 200

```json
{
  "estado": "Cancelada",
  "historial": [
    {
      "fecha": "2026-11-06T14:12:54",
      "estado_anterior": null,
      "estado_nuevo": "Pendiente",
      "usuario": "crojas",
      "nota": "Reserva creada; cupos apartados"
    },
    {
      "fecha": "2026-11-06T14:12:54",
      "estado_anterior": "Pendiente",
      "estado_nuevo": "Pagada",
      "usuario": "crojas",
      "nota": "Pagos cubren el total (2 pago(s))"
    },
    {
      "fecha": "2026-11-06T14:12:54",
      "estado_anterior": "Pagada",
      "estado_nuevo": "Cancelada",
      "usuario": "crojas",
      "nota": "Cambio de planes"
    }
  ]
}
```

### Sillas disponibles antes y después de cancelar

```json
{
  "antes": {
    "LA4101 Básica": 18,
    "LA4102 Básica": 18
  },
  "despues": {
    "LA4101 Básica": 20,
    "LA4102 Básica": 20
  }
}
```

### Pago sobre la reserva cancelada → HTTP 409

```json
{
  "detail": "No se aceptan pagos: la reserva RSV-000026 está cancelada"
}
```

### Cancelar dos veces → HTTP 409

```json
{
  "detail": "La reserva RSV-000026 ya estaba cancelada"
}
```

### Reserva inexistente → HTTP 404

```json
{
  "detail": "No existe la reserva RSV-000000"
}
```

## 7. Reportes B1 a B3 (pipelines de agregación)

### GET /reportes/ventas-por-mes → HTTP 200 — B1. Ventas por mes

```json
[
  {
    "total_vendido": 14000900,
    "total_recaudado": 11880100,
    "reservas": 5,
    "anio": 2026,
    "mes": 8,
    "periodo": "2026-08",
    "ticket_promedio": 2800180.0
  },
  {
    "total_vendido": 22084550,
    "total_recaudado": 14792000,
    "reservas": 6,
    "anio": 2026,
    "mes": 9,
    "periodo": "2026-09",
    "ticket_promedio": 3680758.0
  },
  {
    "total_vendido": 14567200,
    "total_recaudado": 8419400,
    "reservas": 6,
    "anio": 2026,
    "mes": 10,
    "periodo": "2026-10",
    "ticket_promedio": 2427867.0
  },
  {
    "total_vendido": 7548100,
    "total_recaudado": 1762000,
    "reservas": 3,
    "anio": 2026,
    "mes": 11,
    "periodo": "2026-11",
    "ticket_promedio": 2516033.0
  }
]
```

### GET /reportes/destinos-mas-vendidos → HTTP 200 — B2. Destinos más vendidos

```json
[
  {
    "ciudad": "Cartagena",
    "ingresos": 20152000,
    "pasajeros": 16,
    "reservas": 7,
    "iata": "CTG"
  },
  {
    "ciudad": "San Andrés",
    "ingresos": 14759350,
    "pasajeros": 11,
    "reservas": 4,
    "iata": "ADZ"
  },
  {
    "ciudad": "Riohacha",
    "ingresos": 13991200,
    "pasajeros": 11,
    "reservas": 4,
    "iata": "RCH"
  },
  {
    "ciudad": "Santa Marta",
    "ingresos": 6849200,
    "pasajeros": 7,
    "reservas": 3,
    "iata": "SMR"
  },
  {
    "ciudad": "Medellín",
    "ingresos": 2449000,
    "pasajeros": 3,
    "reservas": 2,
    "iata": "MDE"
  }
]
```

### GET /reportes/ocupacion-vuelos → HTTP 200 — B3. Ocupación de vuelos (primeros 8)

```json
[
  {
    "codigo": "AV9701",
    "aerolinea": "Avianca",
    "salida": "2026-11-13T07:00:00",
    "ruta": "BOG → RCH",
    "sillas_totales": 40,
    "sillas_vendidas": 9,
    "ocupacion_pct": 22.5
  },
  {
    "codigo": "AV9702",
    "aerolinea": "Avianca",
    "salida": "2026-11-17T16:00:00",
    "ruta": "RCH → BOG",
    "sillas_totales": 40,
    "sillas_vendidas": 9,
    "ocupacion_pct": 22.5
  },
  {
    "codigo": "AV9601",
    "aerolinea": "Avianca",
    "salida": "2026-11-26T09:00:00",
    "ruta": "BOG → ADZ",
    "sillas_totales": 40,
    "sillas_vendidas": 7,
    "ocupacion_pct": 17.5
  },
  {
    "codigo": "AV9602",
    "aerolinea": "Avianca",
    "salida": "2026-12-01T15:00:00",
    "ruta": "ADZ → BOG",
    "sillas_totales": 40,
    "sillas_vendidas": 7,
    "ocupacion_pct": 17.5
  },
  {
    "codigo": "LA4203",
    "aerolinea": "LATAM",
    "salida": "2026-11-21T08:00:00",
    "ruta": "BOG → SMR",
    "sillas_totales": 40,
    "sillas_vendidas": 6,
    "ocupacion_pct": 15.0
  },
  {
    "codigo": "LA4204",
    "aerolinea": "LATAM",
    "salida": "2026-11-24T17:00:00",
    "ruta": "SMR → BOG",
    "sillas_totales": 40,
    "sillas_vendidas": 6,
    "ocupacion_pct": 15.0
  },
  {
    "codigo": "AV9401",
    "aerolinea": "Avianca",
    "salida": "2026-11-09T07:00:00",
    "ruta": "BOG → CTG",
    "sillas_totales": 40,
    "sillas_vendidas": 5,
    "ocupacion_pct": 12.5
  },
  {
    "codigo": "AV9402",
    "aerolinea": "Avianca",
    "salida": "2026-11-12T19:00:00",
    "ruta": "CTG → BOG",
    "sillas_totales": 40,
    "sillas_vendidas": 5,
    "ocupacion_pct": 12.5
  }
]
```
