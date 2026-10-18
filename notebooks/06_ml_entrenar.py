# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 06 · Entrenar el modelo de habitabilidad (extra)
# MAGIC
# MAGIC El catálogo de expertos de la UPR dejó de actualizarse en marzo de 2024. La idea es entrenar un modelo con el criterio de esos expertos (los planetas que ellos sí evaluaron) para usarlo con los planetas nuevos que todavía no han visto.
# MAGIC
# MAGIC **Por qué no basta con mi regla.** Mi regla de zona habitable usa los límites de una estrella como el Sol, y casi todos sus errores contra los expertos están en estrellas más frías. La zona habitable se corre según la temperatura de la estrella, y eso un modelo lo puede aprender de los datos.
# MAGIC
# MAGIC Este notebook se corre a mano cuando quiero reentrenar. Compara varios modelos con validación cruzada, registra cada uno como una corrida en MLflow y deja marcado el elegido. El job no reentrena: solo usa el modelo elegido en `07_ml_predecir`.

# COMMAND ----------

# MAGIC %md
# MAGIC Fijo la versión de scikit-learn, la misma que en `07_ml_predecir` y en la app. El job y este notebook pueden correr en ambientes serverless distintos, y un modelo guardado con una versión de scikit-learn no se puede abrir con otra (me pasó: `AttributeError ... CyHalfBinomialLoss` al cargarlo desde el job).

# COMMAND ----------

# MAGIC %pip install -q scikit-learn==1.5.2

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import re

import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, PolynomialFeatures, StandardScaler

dbutils.widgets.text("catalogo", "pf_ledezma", "Catálogo")
catalogo = dbutils.widgets.get("catalogo")
assert re.fullmatch(r"[a-z0-9_]+", catalogo), f"Nombre de catálogo inválido: {catalogo}"

# En serverless de Free Edition hay que decirle a MLflow a dónde apuntar; si no, falla buscando
# spark.mlflow.modelRegistryUri. Registrar en Unity Catalog no está permitido en Free Edition,
# así que el modelo vive en el experimento y se carga con runs:/<run_id>/modelo.
mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks")
usuario = spark.sql("SELECT current_user()").first()[0]
experimento = f"/Users/{usuario}/planetas-habitables-ml-{catalogo}"
mlflow.set_experiment(experimento)

SEMILLA = 42
BASICAS = ["radio_tierras", "insolacion_tierras", "temp_estrella_k"]
TODAS = BASICAS + ["periodo_dias", "masa_tierras", "temp_equilibrio_k", "distancia_orbital_ua", "excentricidad"]

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1. Los datos
# MAGIC - **Para entrenar:** planetas que los expertos evaluaron, con datos suficientes y sin los que la NASA tiene en disputa (su existencia todavía se discute).
# MAGIC - **Etiqueta:** habitable si los expertos dicen conservador u optimista.
# MAGIC - **Variables:** solo propiedades físicas del planeta, su órbita y su estrella. No uso el veredicto ni el ESI de los expertos (sería copiar la respuesta), ni mi propia regla, ni la distancia a la Tierra o el año de descubrimiento (no dicen nada de si un planeta es habitable).

# COMMAND ----------

planetas = spark.sql(f"""
  SELECT p.planeta, p.evaluado_por_expertos, p.habitable_expertos, r.potencialmente_habitable AS regla,
         {', '.join(f'p.{c}' for c in TODAS)}
  FROM {catalogo}.silver.planetas p
  JOIN {catalogo}.gold.ranking_habitabilidad r USING (planeta)
  WHERE p.datos_suficientes AND NOT p.en_disputa
""").toPandas()

entrenar = planetas[planetas.evaluado_por_expertos].reset_index(drop=True)
y = (entrenar.habitable_expertos != "no").astype(int)
display(pd.DataFrame({
    "grupo": ["para entrenar (evaluados por expertos)", "para predecir (sin evaluar)"],
    "planetas": [len(entrenar), int((~planetas.evaluado_por_expertos).sum())],
    "habitables": [int(y.sum()), None],
    "porcentaje_habitables": [round(100 * y.mean(), 2), None],
}))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2. ¿Por qué no medir con accuracy?
# MAGIC Casi todos los planetas son "no habitables". Un modelo que siempre dijera "no" tendría un accuracy altísimo y no encontraría ningún planeta. Por eso mido **precisión** (de los que dice habitables, cuántos lo son), **recall** (de los habitables, cuántos encuentra), **F1** y **PR-AUC**.

# COMMAND ----------

regla = (entrenar.regla != "no").astype(int)
display(pd.DataFrame([
    {"modelo": "decir siempre 'no'", "accuracy": round(1 - y.mean(), 3), "recall": 0.0, "f1": 0.0},
    {"modelo": "mi regla (zona habitable del Sol + tamaño)", "accuracy": round((regla == y).mean(), 3),
     "recall": round(recall_score(y, regla), 3), "f1": round(f1_score(y, regla), 3)},
]))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3. Los candidatos, con validación cruzada
# MAGIC Con tan pocos planetas habitables, una sola división entre entrenamiento y prueba es muy ruidosa. Uso validación cruzada estratificada (5 partes, repetida 3 veces) y reporto el promedio y la desviación. Cada candidato queda registrado como una corrida en MLflow.

# COMMAND ----------

def logistica() -> Pipeline:
    """Logística sobre log(radio), log(luz) y temperatura, con términos al cuadrado para poder dibujar una franja."""
    preparar = ColumnTransformer([
        ("log", FunctionTransformer(np.log10), ["radio_tierras", "insolacion_tierras"]),
        ("temp", SimpleImputer(strategy="median"), ["temp_estrella_k"]),
    ])
    return Pipeline([("preparar", preparar), ("cuadrado", PolynomialFeatures(2)), ("escalar", StandardScaler()),
                     ("modelo", LogisticRegression(max_iter=2000))])


def boosting() -> HistGradientBoostingClassifier:
    """Árboles de gradient boosting: aceptan nulos sin rellenarlos (la masa falta en más de la mitad)."""
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1, max_iter=200, random_state=SEMILLA)


candidatos = [
    {"nombre": "regresión logística (3 variables)", "variables": BASICAS, "crear": logistica, "complejidad": 1},
    {"nombre": "gradient boosting (3 variables)", "variables": BASICAS, "crear": boosting, "complejidad": 2},
    {"nombre": "gradient boosting (8 variables)", "variables": TODAS, "crear": boosting, "complejidad": 3},
]

validacion = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=SEMILLA)
metricas = {"precision": "precision", "recall": "recall", "f1": "f1", "pr_auc": "average_precision", "roc_auc": "roc_auc"}

resultados = []
with mlflow.start_run(run_name="mi regla (línea base)"):
    mlflow.set_tags({"tipo": "linea_base", "elegido": "no"})
    mlflow.log_metrics({"precision": precision_score(y, regla), "recall": recall_score(y, regla), "f1": f1_score(y, regla)})
resultados.append({"modelo": "mi regla (línea base)", "variables": 3, "precision": precision_score(y, regla),
                   "recall": recall_score(y, regla), "f1": f1_score(y, regla), "f1_desv": 0.0,
                   "pr_auc": None, "pr_auc_desv": None, "complejidad": 0})

for c in candidatos:
    cv = cross_validate(c["crear"](), entrenar[c["variables"]], y, cv=validacion, scoring=metricas)
    fila = {"modelo": c["nombre"], "variables": len(c["variables"]), "complejidad": c["complejidad"]}
    for m in metricas:
        fila[m] = cv[f"test_{m}"].mean()
    fila["f1_desv"], fila["pr_auc_desv"] = cv["test_f1"].std(), cv["test_pr_auc"].std()
    with mlflow.start_run(run_name=c["nombre"]):
        mlflow.set_tags({"tipo": "candidato", "elegido": "no"})
        mlflow.log_params({"variables": ", ".join(c["variables"]), "validacion": "estratificada 5x3"})
        mlflow.log_metrics({f"cv_{m}": fila[m] for m in metricas} | {"cv_f1_desv": fila["f1_desv"], "cv_pr_auc_desv": fila["pr_auc_desv"]})
    resultados.append(fila)

comparacion = pd.DataFrame(resultados)
display(comparacion.drop(columns="complejidad").round(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4. Cuál elijo
# MAGIC Regla: me quedo con el modelo **más simple** cuyo PR-AUC esté dentro de una desviación estándar del mejor. Si dos modelos rinden igual dentro del ruido, el más simple es más fácil de explicar y de usar (la app lo usa en el simulador con solo tres controles).

# COMMAND ----------

entrenados = comparacion[comparacion.complejidad > 0]
mejor = entrenados.loc[entrenados.pr_auc.idxmax()]
suficientes = entrenados[entrenados.pr_auc >= mejor.pr_auc - mejor.pr_auc_desv]
elegido_nombre = suficientes.sort_values("complejidad").iloc[0].modelo
elegido = next(c for c in candidatos if c["nombre"] == elegido_nombre)
print(f"Mejor PR-AUC: {mejor.modelo} ({mejor.pr_auc:.3f} ± {mejor.pr_auc_desv:.3f})")
print(f"Elegido: {elegido_nombre} (el más simple dentro de una desviación del mejor)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5. Prueba final y modelo elegido
# MAGIC Guardo un 25% de los planetas que el modelo nunca ve, mido ahí, y al final lo entreno con todos los datos para dejarlo listo. Lo registro en MLflow con la etiqueta `elegido = si`, que es la que busca `07_ml_predecir`.

# COMMAND ----------

X = entrenar[elegido["variables"]]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEMILLA)
modelo_prueba = elegido["crear"]().fit(X_tr, y_tr)
prob_te = modelo_prueba.predict_proba(X_te)[:, 1]
pred_te = (prob_te >= 0.5).astype(int)
prueba = {"test_precision": precision_score(y_te, pred_te), "test_recall": recall_score(y_te, pred_te),
          "test_f1": f1_score(y_te, pred_te), "test_pr_auc": average_precision_score(y_te, prob_te),
          "test_roc_auc": roc_auc_score(y_te, prob_te)}
vn, fp, fn, vp = confusion_matrix(y_te, pred_te).ravel()

importancia = permutation_importance(modelo_prueba, X_te, y_te, scoring="average_precision", n_repeats=20,
                                     random_state=SEMILLA)
tabla_importancia = (pd.DataFrame({"variable": elegido["variables"], "importancia": importancia.importances_mean})
                     .sort_values("importancia", ascending=False))

modelo_final = elegido["crear"]().fit(X, y)
fila_elegida = comparacion[comparacion.modelo == elegido_nombre].iloc[0]
with mlflow.start_run(run_name=f"elegido: {elegido_nombre}") as corrida:
    mlflow.set_tags({"tipo": "elegido", "elegido": "si", "catalogo": catalogo})
    mlflow.log_params({"modelo": elegido_nombre, "variables": ", ".join(elegido["variables"]),
                       "planetas_entrenamiento": len(X), "habitables_entrenamiento": int(y.sum())})
    mlflow.log_metrics({f"cv_{m}": fila_elegida[m] for m in metricas} | prueba)
    mlflow.log_dict({"importancia": tabla_importancia.to_dict(orient="records")}, "importancia.json")
    mlflow.sklearn.log_model(modelo_final, "modelo", input_example=X.dropna().head(3))

display(pd.DataFrame([{k.replace("test_", ""): round(v, 3) for k, v in prueba.items()}]))
display(pd.DataFrame({"": ["realmente habitable", "realmente no habitable"],
                      "el modelo dice habitable": [vp, fp], "el modelo dice no": [fn, vn]}))
display(tabla_importancia.round(3))
print(f"Experimento: {experimento}")
print(f"Corrida del modelo elegido: {corrida.info.run_id}")
