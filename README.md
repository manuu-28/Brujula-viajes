# Brújula Viajes 

- Juan Felipe Cortés
- Sara Patiño
- Manuela Vergara

Sistema de una agencia que vende tiquetes, noches de hotel, tours y paquetes. Muestra la disponibilidad real, no vende lo que no tiene
y reporta ventas por mes, destinos y ocupación de vuelos.

```

## Estructura

```
brujula-viajes/
├── api/
│   ├── app/
│   │   ├── main.py           
│   │   ├── database.py      
│   │   ├── setup_db.py      
│   │   ├── schemas.py      
│   │   ├── reportes.py  
│   │   ├── utils.py
│   │   ├── services/
│   │   │   ├── inventario.py 
│   │   │   └── reservas.py   
│   │   └── routers/
│   └── requirements.txt
├── frontend/
│   ├── app.py                
│   └── requirements.txt
├── scripts/
│   ├── seed.py               
│   ├── evidencias.py      
│   └── validador_mongosh.js   
├── evidencias/evidencias.md   
├── docker-compose.yml        
└── .env.example
```

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
