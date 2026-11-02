# Pre-entrega: Construcción de un Pipeline de Ingesta y Limpieza

Pipeline en Python que **extrae** el dataset de reservas hoteleras (el mismo
de la [pre-entrega 3](https://github.com/tomybezzana-cloud/coderhouse-datascienceII/tree/main/11-preentrega-propuesta-ml-hoteleria)), lo
**transforma** (duplicados, nulos, nombres de columnas, valores inválidos) y lo
**carga** en un archivo Parquet listo para entrenar un modelo que prediga
cancelaciones.

El código está dividido en módulos: `main.py` solo ejecuta las etapas y la
lógica vive en `src/`.

## Estructura

```
pipeline-ingesta-limpieza/
├── main.py                  # Ejecuta el pipeline (extracción → transformación → carga)
├── src/
│   ├── config.py            # Rutas, URL del dataset y tipos de datos de cada columna
│   ├── extraccion.py        # Descarga y lectura tipada del CSV
│   ├── transformacion.py    # Funciones de limpieza (una por paso) + limpiar()
│   └── carga.py             # Exportación a Parquet y verificación
├── data/
│   ├── raw/                 # CSV original (lo descarga main.py; NO se sube, ver .gitignore)
│   └── processed/
│       └── reservas_limpias.parquet   # Salida del pipeline
├── requirements.txt
└── .gitignore
```

## Dataset

[Hotel Booking Demand (Kaggle)](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand):
119.390 reservas × 32 columnas de dos hoteles de Portugal (2015-2017).
Antonio, de Almeida y Nunes (2019), *Data in Brief* 22,
[doi.org/10.1016/j.dib.2018.11.126](https://doi.org/10.1016/j.dib.2018.11.126).

Kaggle pide iniciar sesión para descargar, así que el pipeline baja el mismo
archivo desde un espejo público de
[TidyTuesday](https://github.com/rfordatascience/tidytuesday/tree/master/data/2020/2020-02-11)
en GitHub. El CSV pesa ~17 MB y **no se sube al repositorio**: la carpeta
`data/raw/` está en el [`.gitignore`](.gitignore).

## Instalación y ejecución

Requiere Python 3.10 o superior. Probado con Python 3.13, pandas 3.0.3 y
pyarrow 25.0.1.

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone https://github.com/tomybezzana-cloud/pipeline-ingesta-limpieza.git
cd pipeline-ingesta-limpieza

# 2. (Opcional) crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el pipeline
python main.py
```

La primera vez descarga el CSV en `data/raw/hotel_bookings.csv`; las
siguientes lo reutiliza. **Sin internet:** se puede bajar el CSV de Kaggle a
mano y guardarlo con ese nombre en esa carpeta.

El resultado queda en `data/processed/reservas_limpias.parquet`.

### Salida esperada

```
[INFO] pipeline: === 1/3 Extracción ===
[INFO] src.extraccion: Leídas 119,390 filas x 32 columnas (6.1 MB en memoria)
[INFO] pipeline: === 2/3 Transformación ===
[INFO] src.transformacion: Columnas normalizadas a snake_case (0 renombradas)
[INFO] src.transformacion: Duplicados eliminados: 31,994
[INFO] src.transformacion: Nulos antes: children=4, country=452, agent=12,193, company=82,137
[INFO] src.transformacion: Nulos después: 0
[INFO] src.transformacion: Filas inválidas eliminadas: 167 (sin huéspedes o tarifa negativa); meal 'Undefined' unificado con 'SC'
[INFO] src.transformacion: Columnas con fuga de información eliminadas: ['reservation_status', 'reservation_status_date']
[INFO] pipeline: === 3/3 Carga ===
[INFO] src.carga: Parquet guardado en ...\reservas_limpias.parquet (0.92 MB)
[INFO] src.carga: Verificación OK: el Parquet conserva filas, columnas y tipos
[INFO] pipeline: Listo en 5.5 s: 119,390 -> 87,229 filas, 30 columnas, 3.3 MB en memoria. CSV 16.9 MB -> Parquet 0.92 MB
```

Si la descarga o la escritura fallan, el script muestra un mensaje de error
(sin traceback) y termina con código de salida 1.

## Etapas del pipeline

### 1. Extracción ([`src/extraccion.py`](src/extraccion.py))

- `descargar_dataset()`: baja el CSV solo si no existe. Lo escribe primero en
  un archivo `.part` y lo renombra al terminar, así una descarga cortada no
  deja un CSV incompleto.
- `leer_csv()`: lee con `pd.read_csv` pasándole **el tipo de cada columna**
  (definido en [`src/config.py`](src/config.py)) en lugar de dejar que pandas
  lo adivine:

| Tipo de columna | Tipo por defecto de pandas | Tipo elegido | Por qué |
|---|---|---|---|
| Texto con pocos valores (`hotel`, `meal`, `country`...) | `str` | `category` | Guarda cada texto una sola vez y en las filas solo un código entero |
| Enteros chicos (`adults`, `is_canceled`...) | `int64` (8 bytes) | `int8` (1 byte) | Ningún valor pasa de 127 |
| Enteros medianos (`lead_time`, `arrival_date_year`...) | `int64` | `int16` | Máximo 737, entra en 2 bytes |
| Enteros con nulos (`children`, `agent`, `company`) | `float64` | `Int8` / `Int16` | Tipos *nullable*: siguen siendo enteros aunque tengan nulos |
| Tarifa (`adr`) | `float64` | `float32` | Sobra precisión para un precio con 2 decimales |
| `reservation_status_date` | `str` | `datetime64` | Se parsea como fecha desde la lectura |

Además, el CSV escribe los nulos como el texto `"NULL"`; `na_values` hace que
pandas los reconozca como nulos reales.

**Resultado medido:** el mismo CSV ocupa **39,7 MB** en memoria leído sin
tipos y **6,1 MB** con tipos (−85%). Con un dataset 10 o 100 veces más grande,
esta diferencia define si entra o no en la RAM.

### 2. Transformación ([`src/transformacion.py`](src/transformacion.py))

Cada paso es una función independiente que recibe un DataFrame y devuelve uno
nuevo. `limpiar()` las encadena con `.pipe()`:

```python
df.pipe(normalizar_columnas)
  .pipe(eliminar_duplicados)
  .pipe(gestionar_nulos)
  .pipe(corregir_inconsistencias)
  .pipe(eliminar_columnas_con_fuga)
```

**a) `normalizar_columnas`:** pasa los nombres a `snake_case`, sin tildes,
en minúsculas y con `_` en lugar de espacios o símbolos (`"Arrival Date
(Year)"` → `arrival_date_year`). Si dos columnas quedan con el mismo nombre,
lanza un error. Este CSV ya venía casi todo en snake_case (0 columnas
renombradas), pero la función deja el pipeline protegido si la fuente cambia
de formato.

**b) `eliminar_duplicados`:** borra **31.994 filas** (26,8%) idénticas en las
32 columnas. El dataset no trae un ID de reserva, así que no se puede
distinguir una copia de una reserva distinta. Para ML, conservarlas les da más
peso a esos casos y, si una copia queda en train y otra en test, infla la
métrica. Se eliminan **antes** de tratar los nulos: completar un nulo podría
volver iguales dos filas que en el origen no lo eran.

> Dato relevante para el modelo: los duplicados eran sobre todo reservas
> canceladas. La tasa de cancelación baja del **37,0%** (crudo) al **27,5%**
> (limpio). Sin deduplicar, el modelo vería un problema distinto al real.

**c) `gestionar_nulos`:** cada columna se trata según lo que significa su nulo:

| Columna | Nulos | Decisión | Justificación |
|---|---|---|---|
| `children` | 4 | Completar con `0` | Es la moda (la gran mayoría viaja sin niños) y son solo 4 filas |
| `country` | 452 | Completar con `"desconocido"` | Son cientos de filas: borrarlas pierde información. Que falte el país puede ser una señal en sí |
| `agent` | 12.193 | Completar con `"sin_agente"` y pasar a `category` | El nulo **significa** "reservó sin agencia", no un dato perdido. Además es un código, no una cantidad: tratarlo como número le haría creer al modelo que el agente 240 es "mayor" que el 9 |
| `company` | 82.137 (94%) | Eliminar la columna y crear `tiene_empresa` (0/1) | Con 94% de nulos el código de empresa casi no aporta, pero el hecho de que la reserva la hizo una empresa sí puede servir |

Resultado: **0 nulos**.

**d) `corregir_inconsistencias`:** valores que no son nulos pero tampoco son
válidos:

- 166 reservas con 0 adultos, 0 niños y 0 bebés, y 1 con tarifa negativa: se
  eliminan (167 filas en total).
- `meal = "Undefined"`: según el paper del dataset equivale a `"SC"` (sin plan
  de comidas). Se unifican para no tener dos categorías que significan lo
  mismo.

**e) `eliminar_columnas_con_fuga`:** quita `reservation_status` y
`reservation_status_date`. Se conocen recién cuando la reserva terminó
(`Canceled` / `Check-Out`), así que con ellas el modelo "vería el futuro"
(*data leakage*). Ya se había señalado en la pre-entrega 3.

### 3. Carga ([`src/carga.py`](src/carga.py))

- `guardar_parquet()`: exporta con `pyarrow` y compresión `snappy`.
- `verificar_parquet()`: relee el archivo y comprueba con
  `assert_frame_equal` que tenga las mismas filas, valores y **tipos** que el
  DataFrame en memoria.

El resultado se guarda en `data/processed/reservas_limpias.parquet` (87.229 filas × 30
columnas) y **sí se sube al repo**, porque pesa menos de 1 MB.

#### ¿Por qué Parquet y no CSV para Machine Learning?

| | CSV | Parquet |
|---|---|---|
| Tamaño del dataset limpio (mismas 87.229 filas) | 10,5 MB | **0,92 MB** (~11 veces menos) |
| Almacenamiento | Por filas, texto plano | **Por columnas**, binario y comprimido |
| Tipos de datos | Se pierden: todo es texto y hay que volver a declararlos al leer | **Se guardan**: `category`, `int8`, fechas vuelven tal cual |
| Leer solo algunas columnas | Hay que leer el archivo entero | Lee solo las columnas pedidas (`pd.read_parquet(..., columns=[...])`) |
| Uso en el ecosistema | Universal | Formato nativo de Spark, Dask, BigQuery, Polars, etc. |

Para ML pesa sobre todo:

1. **Lectura por columnas:** al entrenar se suelen elegir subconjuntos de
   features; Parquet lee solo esas, sin recorrer todo el archivo.
2. **Esquema embebido:** el dataset llega al modelo con los mismos tipos que
   dejó la limpieza, sin riesgo de que `agent` vuelva como número o `country`
   como texto suelto.
3. **Compresión:** las columnas tienen valores parecidos entre sí y se
   comprimen mucho mejor. Con los mismos datos limpios, el CSV pesa 10,5 MB
   y el Parquet 0,92 MB.

## ¿Por qué pandas y no Dask?

El dataset ocupa 6 MB en memoria una vez tipado, así que pandas lo procesa
completo en segundos y Dask solo agregaría complejidad. Si el volumen creciera
hasta no entrar en RAM, el diseño ya está preparado: cada etapa es una función
que recibe y devuelve un DataFrame, y las operaciones usadas (`read_csv` con
`dtype`, `drop_duplicates`, `fillna`, `to_parquet`) existen con la misma
interfaz en `dask.dataframe`.

## Checklist de la consigna

1. **Al menos dos archivos `.py` (ejecución + lógica modular):** `main.py` y
   cuatro módulos en `src/` (`config`, `extraccion`, `transformacion`,
   `carga`).
2. **Transformación que maneja nulos y duplicados:** `eliminar_duplicados()` y
   `gestionar_nulos()`, cada una con su justificación.
3. **Salida en formato Parquet:** `data/processed/reservas_limpias.parquet`.
4. **README con instalación y ejecución:** este archivo.
5. **Extracción con tipos de datos optimizados:** memoria de 39,7 MB a 6,1 MB.
6. **Normalización de nombres de columnas:** `normalizar_columnas()`.

## Errores comunes evitados

- **Subir el dataset original:** `data/raw/` está en el `.gitignore`; el
  pipeline lo descarga solo.
- **Script monolítico:** cada etapa está en su propio módulo y cada paso de
  limpieza es una función separada que se puede probar o reutilizar por su
  cuenta.

---

Tomás Bezzana
