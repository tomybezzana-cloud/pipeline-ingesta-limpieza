"""Etapa de transformación: limpieza del dataset de reservas.

Cada paso es una función independiente que recibe un DataFrame y devuelve uno
nuevo (no modifica el original). `limpiar` las encadena en orden.
"""

import logging
import re
import unicodedata

import pandas as pd

log = logging.getLogger(__name__)

# Columnas que se conocen recién cuando la reserva ya terminó (check-out o
# cancelación). Si quedan, el modelo "ve el futuro" y aprende a leer el
# resultado en vez de predecirlo (data leakage).
COLUMNAS_CON_FUGA = ["reservation_status", "reservation_status_date"]


def normalizar_nombre(nombre: str) -> str:
    """'Arrival Date (Year)' -> 'arrival_date_year'.

    Saca tildes, pasa a minúsculas y reemplaza todo lo que no sea letra o
    número por un guion bajo.
    """
    sin_tildes = (
        unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^0-9a-z]+", "_", sin_tildes.strip().lower()).strip("_")


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica `normalizar_nombre` a todas las columnas (formato snake_case)."""
    nuevos = [normalizar_nombre(c) for c in df.columns]
    if len(set(nuevos)) != len(nuevos):
        raise ValueError(f"Nombres de columna repetidos tras normalizar: {nuevos}")
    cambiados = sum(a != b for a, b in zip(df.columns, nuevos))
    log.info("Columnas normalizadas a snake_case (%d renombradas)", cambiados)
    return df.set_axis(nuevos, axis=1)


def eliminar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina filas idénticas en todas las columnas, conservando la primera.

    El dataset no trae un ID de reserva, así que no hay forma de distinguir
    dos filas idénticas. Para un modelo, dejarlas repetidas le da más peso a
    esos casos y, si una copia cae en train y otra en test, infla la métrica
    de evaluación.
    """
    sin_dup = df.drop_duplicates(keep="first", ignore_index=True)
    log.info("Duplicados eliminados: %s", f"{len(df) - len(sin_dup):,}")
    return sin_dup


def gestionar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """Trata los nulos columna por columna, según lo que significa cada uno.

    - children (muy pocos nulos): se completa con 0, que es la moda (más del
      90% de las reservas no tiene niños). Borrar las filas daría lo mismo,
      pero así no se pierde el resto de la información.
    - country: se completa con "desconocido". No se borran las filas porque
      son cientos, y que el país falte puede ser información en sí.
    - agent: el nulo significa "reservó sin agencia", no un dato perdido. Es
      un código (no una cantidad), así que pasa a categoría con el valor
      "sin_agente".
    - company: le falta a más del 90% de las filas; como código casi no
      aporta. Se elimina y se conserva lo útil como un indicador
      `tiene_empresa` (1 si la reserva la hizo una empresa).
    """
    df = df.copy()
    nulos_antes = df.isna().sum()
    log.info(
        "Nulos antes: %s",
        ", ".join(f"{c}={n:,}" for c, n in nulos_antes[nulos_antes > 0].items()),
    )

    df["children"] = df["children"].fillna(0).astype("int8")

    df["country"] = (
        df["country"].cat.add_categories("desconocido").fillna("desconocido")
    )

    df["agent"] = (
        df["agent"].astype(str).fillna("sin_agente").astype("category")
    )

    df["tiene_empresa"] = df["company"].notna().astype("int8")
    df = df.drop(columns="company")

    restantes = df.isna().sum().sum()
    log.info("Nulos después: %d", restantes)
    return df


def corregir_inconsistencias(df: pd.DataFrame) -> pd.DataFrame:
    """Corrige valores que no son nulos pero tampoco son válidos.

    - Reservas con 0 adultos, 0 niños y 0 bebés: no son una reserva real, se
      eliminan.
    - Tarifa diaria (adr) negativa: no tiene sentido económico, se elimina.
    - meal = "Undefined": según el paper que documenta el dataset, significa
      lo mismo que "SC" (sin plan de comidas). Se unifica.
    """
    huespedes = df["adults"] + df["children"] + df["babies"]
    invalidas = (huespedes == 0) | (df["adr"] < 0)
    df = df.loc[~invalidas].reset_index(drop=True)

    df["meal"] = (
        df["meal"].replace("Undefined", "SC").cat.remove_unused_categories()
    )
    log.info(
        "Filas inválidas eliminadas: %d (sin huéspedes o tarifa negativa); "
        "meal 'Undefined' unificado con 'SC'",
        invalidas.sum(),
    )
    return df


def eliminar_columnas_con_fuga(df: pd.DataFrame) -> pd.DataFrame:
    """Quita las columnas que revelan el desenlace de la reserva."""
    log.info("Columnas con fuga de información eliminadas: %s", COLUMNAS_CON_FUGA)
    return df.drop(columns=COLUMNAS_CON_FUGA)


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Encadena todos los pasos de limpieza en el orden correcto.

    Los duplicados se quitan antes de tratar los nulos: si no, dos filas que
    difieren solo en un nulo podrían quedar iguales después de completarlo y
    se borrarían sin que realmente lo fueran desde el origen.
    """
    return (
        df.pipe(normalizar_columnas)
        .pipe(eliminar_duplicados)
        .pipe(gestionar_nulos)
        .pipe(corregir_inconsistencias)
        .pipe(eliminar_columnas_con_fuga)
    )
