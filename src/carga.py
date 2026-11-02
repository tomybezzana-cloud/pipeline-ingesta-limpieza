"""Etapa de carga: exportación del dataset limpio a Parquet."""

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def guardar_parquet(df: pd.DataFrame, destino: Path) -> Path:
    """Escribe `df` en Parquet (motor pyarrow, compresión snappy)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(destino, engine="pyarrow", compression="snappy", index=False)
    log.info("Parquet guardado en %s (%.2f MB)", destino, destino.stat().st_size / 1e6)
    return destino


def verificar_parquet(df: pd.DataFrame, ruta: Path) -> None:
    """Relee el Parquet y comprueba que los datos y tipos sean los mismos.

    A diferencia de un CSV, Parquet guarda el esquema: las categorías, los
    int8 y las fechas vuelven tal cual, sin tener que declararlos de nuevo.
    """
    releido = pd.read_parquet(ruta, engine="pyarrow")
    try:
        pd.testing.assert_frame_equal(df, releido)
    except AssertionError as e:
        raise ValueError(f"El Parquet releído no coincide con el original: {e}") from e
    log.info("Verificación OK: el Parquet conserva filas, columnas y tipos")


def cargar(df: pd.DataFrame, destino: Path) -> Path:
    """Punto de entrada de la etapa: guarda y verifica."""
    ruta = guardar_parquet(df, destino)
    verificar_parquet(df, ruta)
    return ruta
