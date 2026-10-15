# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 00 · Descargar un lote de la NASA
# MAGIC
# MAGIC Baja mediciones de exoplanetas del NASA Exoplanet Archive (API TAP) y las deja como CSV en el volume `landing`.
# MAGIC Cada corrida escribe una carpeta nueva `lote_N`, que después lee Auto Loader en `01_bronze`.
# MAGIC
# MAGIC Los lotes se separan por `releasedate`, la fecha en que la NASA publicó cada medición:
# MAGIC
# MAGIC | Lote | Qué trae |
# MAGIC |---|---|
# MAGIC | `1` | Lo publicado antes de 2020, más el catálogo de habitabilidad de la UPR (se carga una sola vez) |
# MAGIC | `2` | Lo publicado de 2020 a septiembre de 2026 |
# MAGIC | `siguiente` | Todo lo que la NASA publicó después de la última medición que ya está en bronze |
# MAGIC
# MAGIC Cuando el job está activo, el archivo que escribe este notebook dispara el pipeline solo (trigger por llegada de archivo).

# COMMAND ----------

import os
import re
import sys

sys.path.append(os.path.abspath("../scripts"))
from descargar_datos import HWC_URL, LOTES, bajar, contar_filas, url_consulta

dbutils.widgets.text("catalogo", "pf_ledezma", "Catálogo")
dbutils.widgets.dropdown("lote", "siguiente", ["siguiente", "1", "2"], "Lote")
catalogo = dbutils.widgets.get("catalogo")
lote = dbutils.widgets.get("lote")
assert re.fullmatch(r"[a-z0-9_]+", catalogo), f"Nombre de catálogo inválido: {catalogo}"

landing = f"/Volumes/{catalogo}/bronze/landing"

# COMMAND ----------

def siguiente_numero_de_lote() -> int:
    carpeta = f"{landing}/mediciones"
    if not os.path.exists(carpeta):
        return 1
    numeros = [int(m.group(1)) for nombre in os.listdir(carpeta) if (m := re.fullmatch(r"lote_(\d+)", nombre))]
    return max(numeros, default=0) + 1


def ultima_fecha_cargada() -> str:
    tabla = f"{catalogo}.bronze.mediciones_raw"
    if not spark.catalog.tableExists(tabla):
        raise RuntimeError("Todavía no hay mediciones en bronze: primero carga los lotes 1 y 2 y corre 01_bronze.")
    return spark.sql(f"SELECT date_format(max(releasedate), 'yyyy-MM-dd') FROM {tabla}").first()[0]


def guardar(contenido: bytes, fuente: str, numero: int, nombre: str) -> str:
    """Escribe primero en _tmp y luego lo mueve, para que el trigger nunca vea un archivo a medias."""
    destino = f"{landing}/{fuente}/lote_{numero}/{nombre}"
    if os.path.exists(destino):
        print(f"{destino} ya existe, no lo vuelvo a escribir.")
        return destino
    temporal = f"{landing}/_tmp/{nombre}"
    os.makedirs(os.path.dirname(temporal), exist_ok=True)
    with open(temporal, "wb") as archivo:
        archivo.write(contenido)
    dbutils.fs.mkdirs(os.path.dirname(destino))
    dbutils.fs.mv(temporal, destino)
    return destino

# COMMAND ----------

if lote == "siguiente":
    desde = ultima_fecha_cargada()
    numero = siguiente_numero_de_lote()
    filtro = f"releasedate > '{desde}'"
    print(f"La última medición cargada en bronze es del {desde}. Le pido a la NASA lo publicado después.")
else:
    numero = int(lote)
    filtro = LOTES[numero]

contenido = bajar(url_consulta(filtro))
filas = contar_filas(contenido)

if filas == 0:
    print("La NASA no ha publicado mediciones nuevas desde la última carga. No se escribe ningún lote.")
    dbutils.notebook.exit("sin datos nuevos")

ruta = guardar(contenido, "mediciones", numero, f"mediciones_lote_{numero}.csv")
print(f"Lote {numero}: {filas:,} mediciones en {ruta}")

if lote == "1":
    ruta_hwc = guardar(bajar(HWC_URL), "habitabilidad", 1, "hwc.csv")
    print(f"Catálogo de habitabilidad en {ruta_hwc}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Qué trae el lote
# MAGIC Un vistazo rápido al archivo antes de que lo lea Auto Loader.

# COMMAND ----------

from pyspark.sql import functions as F

nuevo = spark.read.option("header", True).csv(ruta)
display(nuevo.agg(
    F.count("*").alias("mediciones"),
    F.countDistinct("pl_name").alias("planetas"),
    F.min("releasedate").alias("publicado_desde"),
    F.max("releasedate").alias("publicado_hasta"),
))
display(nuevo.select("pl_name", "hostname", "disc_year", "disc_facility", "releasedate")
             .orderBy(F.desc("releasedate"))
             .limit(15))
