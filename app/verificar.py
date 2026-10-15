"""Revisión al arrancar la app: con qué identidad corre y qué puede ver. El resultado queda en los logs de la app."""
from datos import CATALOGO, consultar

try:
    fila = consultar(
        f"SELECT current_user() AS identidad, count(*) AS planetas, count_if(en_disputa) AS en_disputa "
        f"FROM {CATALOGO}.gold.catalogo_publico"
    ).iloc[0]
    print(f"VERIFICACION identidad={fila.identidad} planetas_visibles={fila.planetas} "
          f"en_disputa_visibles={fila.en_disputa}", flush=True)
except Exception as error:  # no detiene la app: solo deja el problema en los logs
    print(f"VERIFICACION fallo: {error!r}", flush=True)
