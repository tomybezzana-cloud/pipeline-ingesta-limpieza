"""
Pre-entrega: Construcción de un Pipeline de Ingesta y Limpieza (ETL) de
reservas hoteleras.

Ejecuta las tres etapas en orden. La lógica de cada una vive en src/:
1. Extracción  (src/extraccion.py): descarga el CSV si falta y lo lee con
   tipos de datos optimizados.
2. Transformación (src/transformacion.py): normaliza columnas, elimina
   duplicados, gestiona nulos y corrige inconsistencias.
3. Carga (src/carga.py): exporta a Parquet y verifica el resultado.

Uso:
    python main.py
"""

import logging
import sys
import time
from urllib.error import URLError

from src.carga import cargar
from src.config import RUTA_CSV, RUTA_PARQUET, URL_DATASET
from src.extraccion import extraer, memoria_mb
from src.transformacion import limpiar

log = logging.getLogger("pipeline")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    inicio = time.perf_counter()

    try:
        log.info("=== 1/3 Extracción ===")
        crudo = extraer(URL_DATASET, RUTA_CSV)

        log.info("=== 2/3 Transformación ===")
        limpio = limpiar(crudo)

        log.info("=== 3/3 Carga ===")
        ruta = cargar(limpio, RUTA_PARQUET)
    except URLError as e:
        log.error("No se pudo descargar el dataset: %s", e.reason)
        log.error("Revisá la conexión o copiá el CSV a mano en %s", RUTA_CSV)
        return 1
    except (OSError, ValueError, KeyError) as e:
        log.error("El pipeline falló: %s", e)
        return 1

    log.info(
        "Listo en %.1f s: %s -> %s filas, %d columnas, %.1f MB en memoria. "
        "CSV %.1f MB -> Parquet %.2f MB",
        time.perf_counter() - inicio,
        f"{len(crudo):,}", f"{len(limpio):,}", limpio.shape[1], memoria_mb(limpio),
        RUTA_CSV.stat().st_size / 1e6, ruta.stat().st_size / 1e6,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
