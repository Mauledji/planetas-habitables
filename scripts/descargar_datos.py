"""
Descarga los lotes de datos del proyecto.

- Mediciones de exoplanetas: NASA Exoplanet Archive, tabla ps (una fila por publicacion).
  Los lotes se separan por releasedate, la fecha en que la NASA publico cada medicion.
- Catalogo de habitabilidad: Habitable Worlds Catalog (PHL, Universidad de Puerto Rico).

Uso:
    python scripts/descargar_datos.py 1      -> mediciones publicadas antes de 2020 + catalogo HWC
    python scripts/descargar_datos.py 2      -> mediciones de 2020 a septiembre 2026
    python scripts/descargar_datos.py 3      -> mediciones desde el 1 de octubre 2026 (demo en vivo)
"""
import sys
import urllib.parse
import urllib.request
from pathlib import Path

NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
HWC_URL = "https://www.hpcf.upr.edu/~abel/phl/hwc/data/hwc.csv"

COLUMNAS = [
    "pl_name", "hostname", "default_flag", "sy_snum", "sy_pnum",
    "discoverymethod", "disc_year", "disc_facility", "disc_locale", "disc_telescope",
    "soltype", "pl_controv_flag", "pl_refname",
    "pl_orbper", "pl_orbsmax", "pl_rade", "pl_radj", "pl_bmasse", "pl_bmassj",
    "pl_orbeccen", "pl_insol", "pl_eqt",
    "st_spectype", "st_teff", "st_rad", "st_mass", "st_met", "st_lum", "st_age",
    "ra", "dec", "sy_dist", "sy_vmag",
    "rowupdate", "pl_pubdate", "releasedate",
]

LOTES = {
    1: "releasedate < '2020-01-01'",
    2: "releasedate >= '2020-01-01' and releasedate < '2026-10-01'",
    3: "releasedate >= '2026-10-01'",
}

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "datos"


def descargar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    peticion = urllib.request.Request(url, headers={"User-Agent": "proyecto-final-ledezma"})
    with urllib.request.urlopen(peticion, timeout=300) as respuesta:
        contenido = respuesta.read()
    if contenido.lstrip().startswith(b"<"):
        raise RuntimeError(f"La respuesta no es CSV (posible bloqueo del sitio): {url}")
    destino.write_bytes(contenido)
    filas = contenido.count(b"\n") - 1
    print(f"OK {destino.relative_to(CARPETA_DATOS.parent)}  ({filas:,} filas, {len(contenido) / 1e6:.1f} MB)")


def url_lote(lote: int) -> str:
    consulta = f"select {','.join(COLUMNAS)} from ps where {LOTES[lote]}"
    return NASA_TAP + "?" + urllib.parse.urlencode({"query": consulta, "format": "csv"})


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit() or int(sys.argv[1]) not in LOTES:
        print(__doc__)
        sys.exit(1)

    lote = int(sys.argv[1])
    descargar(url_lote(lote), CARPETA_DATOS / "mediciones" / f"lote_{lote}" / f"mediciones_lote_{lote}.csv")

    # El catalogo de habitabilidad no cambia (ultima actualizacion marzo 2024), se baja solo con el lote 1
    if lote == 1:
        descargar(HWC_URL, CARPETA_DATOS / "habitabilidad" / "lote_1" / "hwc.csv")


if __name__ == "__main__":
    main()
