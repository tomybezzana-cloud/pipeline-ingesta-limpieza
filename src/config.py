"""Rutas, URL de origen y tipos de datos del pipeline."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_CSV = BASE_DIR / "data" / "raw" / "hotel_bookings.csv"
RUTA_PARQUET = BASE_DIR / "data" / "processed" / "reservas_limpias.parquet"

# Espejo público del dataset "Hotel Booking Demand" de Kaggle (mismo archivo:
# 119.390 filas x 32 columnas). Se usa porque Kaggle pide iniciar sesión para
# descargar, y este enlace no.
URL_DATASET = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "master/data/2020/2020-02-11/hotels.csv"
)

# En el CSV los nulos vienen escritos como el texto "NULL".
VALORES_NULOS = ["NULL", "NA", ""]

# Tipos de cada columna al leer el CSV. Por defecto pandas usa int64/float64
# para los números y object para el texto; acá se elige el tipo más chico que
# alcanza para el rango de cada columna.
TIPOS_COLUMNAS = {
    # Texto con pocos valores distintos -> category
    "hotel": "category",
    "arrival_date_month": "category",
    "meal": "category",
    "country": "category",
    "market_segment": "category",
    "distribution_channel": "category",
    "reserved_room_type": "category",
    "assigned_room_type": "category",
    "deposit_type": "category",
    "customer_type": "category",
    "reservation_status": "category",
    # Enteros chicos (máx. < 128) -> int8
    "is_canceled": "int8",
    "arrival_date_week_number": "int8",
    "arrival_date_day_of_month": "int8",
    "stays_in_weekend_nights": "int8",
    "stays_in_week_nights": "int8",
    "adults": "int8",
    "babies": "int8",
    "is_repeated_guest": "int8",
    "previous_cancellations": "int8",
    "previous_bookings_not_canceled": "int8",
    "booking_changes": "int8",
    "required_car_parking_spaces": "int8",
    "total_of_special_requests": "int8",
    # Enteros medianos (máx. < 32.768) -> int16
    "arrival_date_year": "int16",
    "lead_time": "int16",
    "days_in_waiting_list": "int16",
    # Enteros con nulos -> tipos "nullable" de pandas (int64 no admite NaN)
    "children": "Int8",
    "agent": "Int16",
    "company": "Int16",
    # Decimales -> float32 (alcanza para una tarifa con 2 decimales)
    "adr": "float32",
}

COLUMNAS_FECHA = ["reservation_status_date"]
