"""DTO de Pydantic (XxxCreate / XxxResponse)."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

IATA = Field(pattern=r"^[A-Z]{3}$", description="Código IATA de tres letras, p. ej. BOG")
CORREO = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TipoTarifa = Literal["Básica", "Clásica", "Flexible"]
TipoHabitacion = Literal["Sencilla", "Doble", "Familiar", "Suite"]
MedioPago = Literal["Efectivo", "Tarjeta de crédito", "Tarjeta débito", "PSE", "Transferencia"]
EstadoReserva = Literal["Pendiente", "Pagada", "Cancelada"]


class Respuesta(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str


class CiudadCreate(BaseModel):
    iata: str = IATA
    nombre: str = Field(min_length=2)
    departamento: str


class AsesorCreate(BaseModel):
    codigo: str = Field(min_length=2)
    nombre: str = Field(min_length=2)
    correo: str = CORREO
    usuario: str = Field(min_length=3)


class Preferencias(BaseModel):
    destinos_favoritos: list[str] = Field(default_factory=list, max_length=10)
    presupuesto: Optional[float] = Field(default=None, ge=0)
    viaja_con_ninos: Optional[bool] = None


class ClienteCreate(BaseModel):
    documento: str = Field(min_length=5, max_length=20)
    nombre: str = Field(min_length=2)
    correo: str = CORREO
    telefono: str = Field(min_length=7)
    preferencias: Optional[Preferencias] = None


class ClienteResponse(Respuesta):
    documento: str
    nombre: str
    correo: str
    telefono: str


class TarifaIn(BaseModel):
    tipo: TipoTarifa
    precio: float = Field(ge=0)
    equipaje: str
    sillas: int = Field(ge=0, description="Sillas totales de la tarifa")


class VueloCreate(BaseModel):
    codigo: str = Field(pattern=r"^[A-Z0-9]{2}[0-9]{3,4}$", examples=["BV1234"])
    aerolinea: str
    origen: str = IATA
    destino: str = IATA
    salida: datetime
    llegada: datetime
    tarifas: list[TarifaIn] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def _coherencia(self):
        if self.origen == self.destino:
            raise ValueError("El origen y el destino deben ser distintos")
        if self.llegada <= self.salida:
            raise ValueError("La llegada debe ser posterior a la salida")
        if len({t.tipo for t in self.tarifas}) != len(self.tarifas):
            raise ValueError("No se puede repetir el tipo de tarifa")
        return self


class TipoHabitacionIn(BaseModel):
    tipo: TipoHabitacion
    capacidad: int = Field(ge=1, le=10)
    precio_noche: float = Field(ge=0)
    total_habitaciones: int = Field(ge=0)


class HotelCreate(BaseModel):
    nombre: str
    ciudad: str = IATA
    direccion: str
    categoria: int = Field(ge=1, le=5)
    servicios: list[str] = Field(default_factory=list)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    tipos_habitacion: list[TipoHabitacionIn] = Field(min_length=1, max_length=4)
    dias_calendario: int = Field(default=60, ge=1, le=365, description="Noches a abrir desde hoy")


class PuntoEncuentroIn(BaseModel):
    nombre: str
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class SalidaIn(BaseModel):
    fecha: datetime
    precio: float = Field(ge=0)
    cupos: int = Field(ge=0)


class TourCreate(BaseModel):
    nombre: str
    ciudad: str = IATA
    descripcion: str
    duracion_horas: float = Field(gt=0)
    incluye: list[str] = Field(default_factory=list)
    punto_encuentro: PuntoEncuentroIn
    salidas: list[SalidaIn] = Field(min_length=1, max_length=60)


class ComponenteIn(BaseModel):
    tipo: Literal["vuelo", "hotel", "tour"]
    vuelo_codigo: Optional[str] = None
    tarifa: Optional[TipoTarifa] = None
    hotel_id: Optional[str] = None
    tipo_habitacion: Optional[TipoHabitacion] = None
    fecha_entrada: Optional[date] = None
    noches: Optional[int] = Field(default=None, ge=1, le=30)
    tour_id: Optional[str] = None
    salida_id: Optional[str] = None

    @model_validator(mode="after")
    def _campos(self):
        requeridos = {
            "vuelo": ["vuelo_codigo", "tarifa"],
            "hotel": ["hotel_id", "tipo_habitacion", "fecha_entrada", "noches"],
            "tour": ["tour_id", "salida_id"],
        }[self.tipo]
        faltan = [c for c in requeridos if getattr(self, c) is None]
        if faltan:
            raise ValueError(f"Un componente '{self.tipo}' requiere: {', '.join(faltan)}")
        return self


class PaqueteCreate(BaseModel):
    codigo: str = Field(min_length=3)
    nombre: str
    destino: str = IATA
    descuento_pct: float = Field(ge=0, le=100)
    vigencia_desde: date
    vigencia_hasta: date
    componentes: list[ComponenteIn] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def _fechas(self):
        if self.vigencia_hasta < self.vigencia_desde:
            raise ValueError("La vigencia 'hasta' debe ser posterior a 'desde'")
        return self


class ItemIn(BaseModel):
    tipo: Literal["vuelo", "hotel", "tour", "paquete"]
    cantidad: int = Field(ge=1, le=20, description="Sillas, habitaciones, cupos o personas (paquete)")
    vuelo_codigo: Optional[str] = None
    tarifa: Optional[TipoTarifa] = None
    hotel_id: Optional[str] = None
    tipo_habitacion: Optional[TipoHabitacion] = None
    fecha_entrada: Optional[date] = None
    noches: Optional[int] = Field(default=None, ge=1, le=30)
    tour_id: Optional[str] = None
    salida_id: Optional[str] = None
    paquete_codigo: Optional[str] = None

    @model_validator(mode="after")
    def _campos(self):
        requeridos = {
            "vuelo": ["vuelo_codigo", "tarifa"],
            "hotel": ["hotel_id", "tipo_habitacion", "fecha_entrada", "noches"],
            "tour": ["tour_id", "salida_id"],
            "paquete": ["paquete_codigo"],
        }[self.tipo]
        faltan = [c for c in requeridos if getattr(self, c) is None]
        if faltan:
            raise ValueError(f"Un ítem '{self.tipo}' requiere: {', '.join(faltan)}")
        return self


class PasajeroIn(BaseModel):
    nombre: str = Field(min_length=2)
    documento: str = Field(min_length=3)
    fecha_nacimiento: date

    @model_validator(mode="after")
    def _fecha(self):
        if self.fecha_nacimiento > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return self


class ReservaCreate(BaseModel):
    cliente_documento: str
    asesor_codigo: str
    usuario: Optional[str] = Field(default=None, description="Usuario de la aplicación; por defecto, el del asesor")
    items: list[ItemIn] = Field(min_length=1, max_length=30)
    pasajeros: list[PasajeroIn] = Field(min_length=1, max_length=20)


class PagoCreate(BaseModel):
    valor: float = Field(gt=0)
    medio: MedioPago
    usuario: str = Field(min_length=3)


class CancelacionCreate(BaseModel):
    usuario: str = Field(min_length=3)
    motivo: Optional[str] = None


class ReservaResponse(Respuesta):
    codigo: str
    estado: EstadoReserva
    total: float
    total_pagado: float
