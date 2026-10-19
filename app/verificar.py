"""Revisión al arrancar la app: con qué identidad corre, qué puede ver y si carga el modelo (queda en los logs)."""
from datos import CATALOGO, cargar_modelo, consultar

try:
    fila = consultar(
        f"SELECT current_user() AS identidad, count(*) AS planetas, count_if(en_disputa) AS en_disputa "
        f"FROM {CATALOGO}.gold.catalogo_publico"
    ).iloc[0]
    print(f"VERIFICACION identidad={fila.identidad} planetas_visibles={fila.planetas} "
          f"en_disputa_visibles={fila.en_disputa}", flush=True)
    corrida = consultar(f"SELECT max_by(modelo_run_id, predicho_en) AS run_id, count(*) AS predicciones "
                        f"FROM {CATALOGO}.gold.prediccion_habitabilidad").iloc[0]
    modelo = cargar_modelo(corrida.run_id)
    print(f"VERIFICACION modelo={type(modelo).__name__} corrida={corrida.run_id} "
          f"variables={list(modelo.feature_names_in_)} predicciones={corrida.predicciones}", flush=True)
except Exception as error:  # no detiene la app: solo deja el problema en los logs
    print(f"VERIFICACION fallo: {error!r}", flush=True)
