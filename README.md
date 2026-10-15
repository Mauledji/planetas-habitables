# ¿Hay otra Tierra? 🪐

Proyecto final del Módulo 4 (Gestión y gobernanza de datos con Unity Catalog) del Técnico en Ingeniería de Datos con Databricks, Universidad Latina de Costa Rica.

Quería trabajar con datos reales y con un tema que me diera curiosidad de verdad, así que escogí los exoplanetas: planetas que orbitan otras estrellas. Construí en Databricks un pipeline que toma las mediciones de la NASA, las limpia y calcula qué planetas se parecen más a la Tierra, incluidos los que se descubrieron después de la última actualización del catálogo de habitabilidad que usan los expertos. El resultado se puede explorar en una Databricks App.

![Mapa de habitabilidad: planetas según la luz que reciben y su tamaño](docs/mapa_habitabilidad.png)

## El problema

La NASA tiene confirmados más de 6,400 exoplanetas, pero sus datos no vienen listos para usar. Cada planeta aparece una vez por cada artículo científico que lo midió (algunos hasta 34 veces), a muchas mediciones les faltan datos importantes (en la medición oficial, la luz que recibe el planeta falta en el 85% de los casos) y hay detalles como fechas en tres formatos distintos o referencias que vienen como HTML.

Además, el Habitable Worlds Catalog de la Universidad de Puerto Rico, que es la referencia para saber qué planetas podrían ser habitables, se actualizó por última vez en marzo de 2024. Lo que se descubrió después no tiene evaluación.

La pregunta que responde el proyecto es: **¿qué planetas confirmados se parecen más a la Tierra, incluidos los que el catálogo de expertos todavía no evalúa?**

## Los datos

| Fuente | Qué trae | Cómo llega |
|---|---|---|
| [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/), tabla *Planetary Systems* | Una fila por cada medición publicada de cada planeta confirmado. Uso 36 columnas | Por la API TAP de la NASA, en CSV, por lotes |
| [Habitable Worlds Catalog](https://phl.upr.edu/hwc), PHL @ UPR Arecibo | 5,599 planetas con su índice de parecido a la Tierra (ESI) y si son habitables según los expertos | Un CSV que se carga una sola vez |

Los lotes se separan por la fecha en que la NASA publicó cada medición. El lote 1 es lo publicado antes de 2020 (30,671 mediciones), el lote 2 va de 2020 a septiembre de 2026 (9,583) y desde ahí cada lote nuevo trae solo lo que la NASA publicó después de la última carga. Así el proyecto se comporta como un pipeline real, donde los datos van llegando con el tiempo.

## Cómo funciona

```mermaid
flowchart LR
    NASA[("NASA Exoplanet Archive<br/>API TAP")] -->|"00_descargar_lote"| LAND[/"Volume landing<br/>lote_1, lote_2, lote_3..."/]
    UPR[("Habitable Worlds Catalog<br/>UPR")] --> LAND
    LAND -->|"Auto Loader"| BRONZE["BRONZE<br/>mediciones_raw<br/>habitabilidad_raw"]
    BRONZE --> SILVER["SILVER<br/>mediciones<br/>planetas<br/>habitabilidad_expertos"]
    SILVER --> RANK["GOLD<br/>ranking_habitabilidad<br/>(reglas de calidad)"]
    RANK --> PUB["GOLD<br/>catalogo_publico<br/>(row filter)"]
    PUB --> APP["Databricks App<br/>¿Hay otra Tierra?"]
    JOB{{"Lakeflow Job<br/>arranca cuando llega un archivo"}} -.-> BRONZE
    JOB -.-> SILVER
    JOB -.-> RANK
```

1. **Descarga.** El notebook `00_descargar_lote` le pide a la API de la NASA las mediciones publicadas después de la última carga y las deja como CSV en un volume de Unity Catalog (`landing/mediciones/lote_N/`).
2. **Job.** Cuando aparece un archivo nuevo en el volume, el job `pf_ledezma pipeline` arranca solo y corre bronze, silver y gold en orden.
3. **Bronze.** Auto Loader carga solo los archivos que no ha visto antes y guarda en cada fila de qué archivo vino.
4. **Silver.** Deja los tipos correctos, quita las copias exactas, se queda con un registro por planeta, completa los datos que faltan y lo une con el catálogo de la UPR.
5. **Gold.** Calcula el ESI y si el planeta está en la zona habitable. El ranking tiene reglas de calidad y la versión pública tiene un row filter.
6. **App.** La Databricks App lee la versión pública con su propia identidad.

## Lo que encontré

Los planetas más parecidos a la Tierra según el pipeline:

| Planeta | Distancia | ESI (mío) | ESI (expertos UPR) |
|---|---|---|---|
| Teegarden's Star b | 12 años luz | 0.969 | 0.968 |
| TOI-700 d | 102 años luz | 0.925 | 0.941 |
| TOI-700 e | 102 años luz | 0.911 | 0.912 |
| TRAPPIST-1 d | 41 años luz | 0.908 | 0.908 |
| GJ 3378 b | 25 años luz | 0.897 | no lo tiene |

- De 5,290 planetas con datos suficientes, **77 son potencialmente habitables** y **15 de ellos no están en el catálogo de expertos**. Los más interesantes son GJ 3378 b (descubierto en 2026), L 98-59 f (2025) y Gliese 12 b (2024).
- Para revisar que mi cálculo tuviera sentido lo comparé con el de los expertos: en los planetas que ellos sí evaluaron, **coincido en el 99.5%** al decir si un planeta es habitable o no, y la correlación entre los dos ESI es de 0.99.

## Componentes del proyecto

| Parte | Qué hice | Dónde |
|---|---|---|
| Columna vertebral: bronze | Ingesta incremental con Auto Loader desde un volume, con `schemaLocation`, checkpoint y el archivo de origen en cada fila. Dos lotes que entran una sola vez cada uno | `notebooks/01_bronze.py` |
| Columna vertebral: silver | Tipos correctos, copias exactas fuera, deduplicación por planeta, reglas de nulos, join con el catálogo de la UPR y métricas antes y después | `notebooks/02_silver.sql` |
| C1 · Gold y calidad | Ranking de habitabilidad con reglas `NOT NULL` y `CHECK`, y la prueba de una fila que se rechaza | `notebooks/03_gold.sql`, `notebooks/03b_prueba_calidad.sql` |
| C2 · Orquestación | Lakeflow Job con tres tareas (bronze → silver → gold), reintentos y trigger por llegada de archivo | `resources/pipeline_job.yml` |
| C3 · Gobernanza | Esquemas por capa, perfil de lectura con mínimo privilegio, row filter con tabla de mapeo y tags | `notebooks/04_gobernanza.sql` |
| C4 · CI/CD | Git folder conectado a este repo, rama `dev`, pull requests a `main` y bundle con targets `dev` y `prod` | `databricks.yml` |
| C5 · Observabilidad | Auditoría, linaje y corridas del job desde las tablas del sistema, y liquid clustering con `OPTIMIZE` | `notebooks/05_observabilidad.sql` |
| Extra | Databricks App para explorar los planetas | `app/` |

No reemplacé ningún componente con temas opcionales. La app es un extra que hice porque quería que el resultado se pudiera usar, no solo ver en un notebook.

## Decisiones de diseño

**Lotes por fecha de publicación.** Separar los lotes por la fecha en que la NASA publicó cada medición me permite simular cómo llegan los datos en la vida real y, sobre todo, mostrar en vivo un lote nuevo con lo que la NASA publicó esa misma semana.

**Databricks descarga directo de la NASA.** El notebook de descarga escribe primero en una carpeta temporal y después mueve el archivo a su lote, para que el trigger nunca vea un archivo a medias.

**Trigger por llegada de archivo y no programado.** Los datos nuevos llegan cuando la NASA publica, no a una hora fija, así que tiene más sentido que el job arranque cuando hay algo que procesar. Bronze tiene dos reintentos porque es la tarea que depende del volume.

**Un registro por planeta.** La llave del negocio es el nombre del planeta y me quedo con la medición que la NASA marca como oficial, la más reciente. Si todavía no llegó la oficial, uso la más reciente. Esto pasó de verdad con el lote 1: a varios planetas les faltaba su medición oficial, que llegó en el lote 2.

**Nulos sin promedios.** Cada planeta es distinto, así que rellenar con un promedio sería inventar el dato. Primero busco el valor en otra publicación del mismo planeta; si nadie lo midió, lo calculo (la luz que recibe, con la luminosidad de la estrella y la distancia; el radio, con la masa usando la relación de Chen y Kipping de 2017); la distancia que no trae la NASA la tomo del catálogo de la UPR; y lo que sigue faltando se queda nulo. Con esto, los planetas con datos suficientes para el ranking pasaron de 826 a 5,290.

**ESI simplificado y zona habitable conservadora.** Uso la versión del ESI que solo necesita el radio y la luz que recibe el planeta, y los límites de zona habitable de Kopparapu et al. (2013) para una estrella como el Sol. Es una simplificación, por eso comparé el resultado con el de los expertos antes de confiar en él.

**Calidad y seguridad en tablas separadas.** Quería poner las reglas de calidad y el row filter en la misma tabla, pero Unity Catalog no lo permite: una tabla con reglas `CHECK` no acepta row filter ni column mask. Por eso `ranking_habitabilidad` lleva las reglas y `catalogo_publico`, que es la que se publica, lleva el filtro.

**Quién ve qué.** Los planetas que la NASA tiene "en disputa" solo los ve quien tenga nivel `investigador` en la tabla de mapeo `gobernanza.mapa_acceso`. El perfil de lectura (`account users`) solo puede leer lo publicado en gold. La app cae en ese perfil: según sus propios logs ve 5,258 planetas, sin los 32 en disputa.

**Liquid clustering por planeta.** La ficha de la app pide todas las mediciones de un planeta, así que agrupé `silver.mediciones` por `planeta` en vez de particionar, porque hay miles de planetas y saldrían miles de particiones pequeñas.

**Silver y gold se reconstruyen completas.** Son unas 40 mil filas, así que reconstruirlas en cada corrida es simple y rápido. Si el volumen creciera mucho, cambiaría a `MERGE` o a tablas de streaming.

**Dos ambientes con el mismo código.** Todos los notebooks reciben el catálogo como parámetro. El bundle despliega a `dev` (`pf_ledezma_dev`, con el trigger en pausa) para probar, y a `prod` (`pf_ledezma`) con el trigger activo y la app.

## Cómo se corre

Necesitas un workspace de Databricks (sirve Free Edition) y el [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/).

1. Clona este repo como Git folder en Databricks o en tu compu.
2. En Databricks, corre `notebooks/00_config` para crear el catálogo, los esquemas y el volume.
3. Despliega el job y la app (el trigger del job vigila el volume, por eso va después del paso 2):
   ```bash
   databricks bundle deploy -t prod
   ```
4. Corre `notebooks/00_descargar_lote` con el parámetro **Lote = 1**. El archivo llega al volume y el job carga bronze, silver y gold solo. Después repite con **Lote = 2**.
5. Corre `notebooks/04_gobernanza` (permisos, row filter y tags) y `notebooks/05_observabilidad`.
6. Arranca la app:
   ```bash
   databricks bundle run app -t prod
   ```
7. Para traer lo nuevo de la NASA, corre `00_descargar_lote` con **Lote = siguiente**: si hay mediciones nuevas, el job arranca solo.

Para probar cambios sin tocar prod, usa `-t dev`. Ahí el trigger está en pausa y el job se corre a mano con `databricks bundle run pipeline -t dev`.

## Estructura del repositorio

```
├── app/                    Databricks App (Streamlit)
├── docs/                   Imágenes del README
├── notebooks/
│   ├── 00_config.py              catálogo, esquemas y volume
│   ├── 00_descargar_lote.py      descarga un lote de la NASA al volume
│   ├── 01_bronze.py              Auto Loader
│   ├── 02_silver.sql             limpieza, deduplicación, nulos y join
│   ├── 03_gold.sql               ranking, reglas de calidad y catálogo público
│   ├── 03b_prueba_calidad.sql    fila que se rechaza (no va en el job)
│   ├── 04_gobernanza.sql         permisos, row filter y tags
│   └── 05_observabilidad.sql     tablas del sistema y liquid clustering
├── resources/pipeline_job.yml    el job
├── scripts/descargar_datos.py    consulta a la NASA (la usa el notebook de descarga)
└── databricks.yml                bundle con targets dev y prod
```

## Créditos

- Este proyecto usa datos del NASA Exoplanet Archive, que opera Caltech bajo contrato con la NASA dentro del Exoplanet Exploration Program.
- The Habitable Worlds Catalog (HWC), PHL @ UPR Arecibo. Datos descargados en octubre de 2026.
- ESI: Schulze-Makuch et al. (2011). Zona habitable: Kopparapu et al. (2013). Relación masa-radio: Chen y Kipping (2017).

Mauricio Ledezma · [mauledji.com](https://mauledji.com)
