// mongosh "mongodb://localhost:27017/brujula_viajes" scripts/validador_mongosh.js

function probar(titulo, fn) {
  try {
    fn();
    print(`✗ ${titulo}: SE INSERTÓ (no debería)`);
  } catch (e) {
    print(`✓ ${titulo}: rechazado -> ${e.message}`);
  }
}

probar("Vuelo con origen 'Bogotá' en lugar de 'BOG'", () =>
  db.vuelos.insertOne({
    codigo: "BV1234", aerolinea: "Avianca",
    origen: { iata: "Bogotá", nombre: "Bogotá" }, destino: { iata: "CTG", nombre: "Cartagena" },
    salida: new Date("2026-12-01T07:00:00Z"), llegada: new Date("2026-12-01T08:25:00Z"),
    tarifas: [{ tipo: "Básica", precio: 250000, equipaje: "Personal", sillas_totales: 20, sillas_disponibles: 20 }]
  }));

probar("Vuelo con fecha como texto y precio negativo", () =>
  db.vuelos.insertOne({
    codigo: "BV1235", aerolinea: "Avianca",
    origen: { iata: "BOG", nombre: "Bogotá" }, destino: { iata: "CTG", nombre: "Cartagena" },
    salida: "2026-12-01 07:00", llegada: new Date("2026-12-01T08:25:00Z"),
    tarifas: [{ tipo: "Básica", precio: -100, equipaje: "Personal", sillas_totales: 20, sillas_disponibles: 20 }]
  }));

probar("Hotel con categoría 7", () =>
  db.hoteles.insertOne({
    nombre: "Hotel X", ciudad: { iata: "CTG", nombre: "Cartagena" }, direccion: "Calle 1", categoria: 7,
    servicios: [], ubicacion: { type: "Point", coordinates: [-75.5, 10.4] },
    tipos_habitacion: [{ tipo: "Doble", capacidad: 2, precio_noche: 300000, total_habitaciones: 5 }]
  }));

probar("Reserva con estado 'Reservada'", () => {
  const r = db.reservas.findOne({}, { _id: 0 });
  r.codigo = "RSV-999999";
  r.estado = "Reservada";
  db.reservas.insertOne(r);
});

probar("Cliente con documento repetido (índice único)", () => {
  const c = db.clientes.findOne({}, { _id: 0 });
  db.clientes.insertOne(c);
});

probar("Vuelo con código repetido (índice único)", () => {
  const v = db.vuelos.findOne({}, { _id: 0 });
  db.vuelos.insertOne(v);
});
