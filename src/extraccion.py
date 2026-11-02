"""Etapa de extracción: descarga (si hace falta) y lectura tipada del CSV."""

import logging
import urllib.request
from pathlib import Path

import pandas as pd

from src.config import COLUMNAS_FECHA, TIPOS_COLUMNAS, VALORES_NULOS

try:
    # Opcional: hace que Python confíe en los certificados del sistema
    # operativo (útil si un antivirus o proxy corporativo inspecciona HTTPS).
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

log = logging.getLogger(__name__)


def descargar_dataset(url: str, destino: Path) -> Path:
    """Descarga el CSV a `destino` solo si todavía no existe."""
    if destino.exists():
        log.info("CSV ya disponible en %s (no se descarga)", destino)
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)
    log.info("Descargando dataset desde %s", url)
    # Se descarga a un archivo temporal y se renombra al final, para no dejar
    # un CSV a medio escribir si la descarga se corta.
    temporal = destino.with_suffix(".part")
    urllib.request.urlretrieve(url, temporal)
    temporal.replace(destino)
    log.info("Descarga completa: %.1f MB", destino.stat().st_size / 1e6)
    return destino


def leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee el CSV aplicando los tipos de `TIPOS_COLUMNAS` y parseando fechas."""
    df = pd.read_csv(
        ruta,
        dtype=TIPOS_COLUMNAS,
        na_values=VALORES_NULOS,
        keep_default_na=False,
        parse_dates=COLUMNAS_FECHA,
    )
    log.info(
        "Leídas %s filas x %s columnas (%.1f MB en memoria)",
        f"{len(df):,}", df.shape[1], memoria_mb(df),
    )
    return df


def memoria_mb(df: pd.DataFrame) -> float:
    """Memoria real ocupada por el DataFrame, incluyendo el texto."""
    return df.memory_usage(deep=True).sum() / 1e6


def extraer(url: str, ruta_csv: Path) -> pd.DataFrame:
    """Punto de entrada de la etapa: asegura el CSV local y lo carga."""
    return leer_csv(descargar_dataset(url, ruta_csv))
