"""Conexión a MongoDB: MongoClient, base de datos y dependencia get_db."""
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "brujula_viajes")

client: MongoClient = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)


def get_database(nombre: str | None = None) -> Database:
    return client[nombre or MONGO_DB]


def get_db() -> Database:
    """Dependencia de FastAPI: entrega la base de datos a cada router."""
    return get_database()
