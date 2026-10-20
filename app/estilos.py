"""Paleta y hoja de estilos de la app: el look de "observatorio de noche".

Los colores tienen significado y se usan igual en el mapa, las tarjetas y el simulador:
verde = zona habitable, violeta = lo que dice el modelo, ámbar = caliente, celeste = frío.
"""
import random
import urllib.parse

import streamlit as st

FONDO = "#060A14"
SUPERFICIE = "#0D1526"
LINEA = "#1D2942"
LINEA_FUERTE = "#2A3A5E"
TEXTO = "#E8EEF8"
TENUE = "#8C9AB3"
APAGADO = "#5E6B85"
ACENTO = "#7AA2FF"
HABITABLE = "#3DDC97"
MODELO = "#B197FC"
CALIENTE = "#F7B955"
FRIO = "#6FD3F2"
FUENTE = "Space Grotesk, sans-serif"
MONO = "JetBrains Mono, monospace"


def _cielo(semilla: int = 11, estrellas: int = 70, lado: int = 720) -> str:
    """Un mosaico SVG de estrellas tenues para el fondo (siempre el mismo, por la semilla)."""
    azar = random.Random(semilla)
    puntos = "".join(
        f"<circle cx='{azar.uniform(0, lado):.0f}' cy='{azar.uniform(0, lado):.0f}' "
        f"r='{azar.choice((0.5, 0.6, 0.7, 0.8, 1.0, 1.2))}' fill='#E8EEF8' "
        f"fill-opacity='{azar.uniform(0.12, 0.6):.2f}'/>"
        for _ in range(estrellas)
    )
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='{lado}' height='{lado}'>{puntos}</svg>"
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)


CSS = """
:root {
  --fondo: #060A14;
  --superficie: rgba(13, 21, 38, 0.74);
  --superficie-solida: #0D1526;
  --superficie-2: #121C33;
  --linea: #1D2942;
  --linea-fuerte: #2A3A5E;
  --texto: #E8EEF8;
  --tenue: #8C9AB3;
  --apagado: #5E6B85;
  --acento: #7AA2FF;
  --habitable: #3DDC97;
  --modelo: #B197FC;
  --caliente: #F7B955;
  --frio: #6FD3F2;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --radio: 18px;
}

/* ---------- Fondo y estructura ---------- */
[data-testid="stApp"] {
  background-color: var(--fondo);
  background-image:
    url("__CIELO__"),
    radial-gradient(900px 520px at 88% -8%, rgba(122, 162, 255, 0.13), transparent 65%),
    radial-gradient(760px 480px at -6% 104%, rgba(61, 220, 151, 0.07), transparent 65%);
  background-size: 720px 720px, auto, auto;
  background-attachment: fixed;
}
[data-testid="stHeader"] {
  background: rgba(6, 10, 20, 0.78);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--linea);
}
[data-testid="stDecoration"] { display: none; }
div:has(> img[data-testid="stHeaderLogo"]), [data-testid="stLogoLink"] {
  display: flex; align-items: center; gap: 0.65rem; }
div:has(> img[data-testid="stHeaderLogo"])::after, [data-testid="stLogoLink"]::after {
  content: "¿Hay otra Tierra?"; font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.02rem;
  letter-spacing: -0.01em; color: var(--texto); white-space: nowrap; margin-right: 1.4rem;
}
[data-testid="stTopNavLink"] { border-radius: 999px; padding: 0.38rem 0.9rem; transition: background 150ms ease; }
[data-testid="stTopNavLink"] p { font-weight: 500; font-size: 0.92rem; color: var(--tenue); }
[data-testid="stTopNavLink"] [data-testid="stIconMaterial"] { color: var(--tenue); }
[data-testid="stTopNavLink"]:hover { background: rgba(122, 162, 255, 0.08); }
[data-testid="stTopNavLink"]:hover p { color: var(--texto); }
[data-testid="stTopNavLink"][aria-current="page"] { background: rgba(122, 162, 255, 0.14);
  box-shadow: inset 0 0 0 1px rgba(122, 162, 255, 0.35); }
[data-testid="stTopNavLink"][aria-current="page"] p,
[data-testid="stTopNavLink"][aria-current="page"] [data-testid="stIconMaterial"] { color: var(--texto); }
@media (max-width: 700px) {
  div:has(> img[data-testid="stHeaderLogo"])::after, [data-testid="stLogoLink"]::after { display: none; }
}
[data-testid="stMainBlockContainer"] { max-width: 1320px; padding-top: 5.75rem; padding-bottom: 3rem; }

/* ---------- Tipografía ---------- */
.ceja {
  font-family: var(--mono); font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--acento); margin: 0 0 0.6rem 0;
}
.titular { font-size: clamp(2.4rem, 1.6rem + 2.6vw, 3.6rem); font-weight: 700; letter-spacing: -0.025em;
  line-height: 1.02; margin: 0; color: var(--texto); }
.titulo-pagina { font-size: clamp(1.9rem, 1.4rem + 1.6vw, 2.6rem); font-weight: 700; letter-spacing: -0.02em;
  line-height: 1.08; margin: 0; color: var(--texto); }
.entrada { font-size: 1.06rem; line-height: 1.6; color: var(--tenue); max-width: 64ch; margin: 0.9rem 0 0 0; }
.mono { font-family: var(--mono); }
.tenue { color: var(--tenue); }
.seccion { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
  border-bottom: 1px solid var(--linea); padding-bottom: 0.6rem; margin: 0.4rem 0 0.2rem 0; }
.seccion h3 { margin: 0; font-size: 1.15rem; font-weight: 600; color: var(--texto); }
.seccion span { font-family: var(--mono); font-size: 0.78rem; color: var(--tenue); }

/* ---------- Franja de instrumentos (métricas) ---------- */
.franja { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 1.8rem;
  border: 1px solid var(--linea); border-radius: var(--radio); background: var(--superficie);
  backdrop-filter: blur(10px); overflow: hidden; }
.dato { padding: 1.05rem 1.3rem 1.1rem 1.3rem; border-left: 1px solid var(--linea); }
.dato:first-child { border-left: none; }
.dato__valor { display: block; font-family: var(--mono); font-size: 1.85rem; font-weight: 500;
  color: var(--texto); letter-spacing: -0.02em; line-height: 1.1; }
.dato__nombre { display: flex; align-items: center; gap: 0.45rem; margin-top: 0.35rem;
  font-size: 0.84rem; color: var(--tenue); }
.punto { width: 7px; height: 7px; border-radius: 50%; background: var(--apagado); flex: none; }
.punto--habitable { background: var(--habitable); box-shadow: 0 0 10px rgba(61, 220, 151, 0.7); }
.punto--modelo { background: var(--modelo); box-shadow: 0 0 10px rgba(177, 151, 252, 0.7); }
.punto--acento { background: var(--acento); box-shadow: 0 0 10px rgba(122, 162, 255, 0.7); }
@media (max-width: 900px) {
  .franja { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dato:nth-child(3) { border-left: none; }
  .dato:nth-child(n+3) { border-top: 1px solid var(--linea); }
}

/* ---------- Tarjetas (contenedores con key) ---------- */
.st-key-ficha, .st-key-simulador, .st-key-veredicto, .st-key-dialogo_ficha,
[class*="st-key-tarjeta_"] {
  background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio);
  padding: 1.3rem 1.35rem 1.2rem 1.35rem; backdrop-filter: blur(10px);
  transition: border-color 160ms ease, transform 160ms ease;
}
[class*="st-key-tarjeta_"]:hover { border-color: var(--linea-fuerte); transform: translateY(-2px); }
.st-key-dialogo_ficha { background: transparent; border: none; padding: 0; backdrop-filter: none; }

/* ---------- Chips ---------- */
.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.7rem 0 0.2rem 0; }
.chip { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.22rem 0.65rem; border-radius: 999px;
  font-size: 0.78rem; font-weight: 500; border: 1px solid var(--linea-fuerte); color: var(--tenue);
  background: rgba(18, 28, 51, 0.6); white-space: nowrap; }
.chip--habitable { color: var(--habitable); border-color: rgba(61, 220, 151, 0.35); background: rgba(61, 220, 151, 0.08); }
.chip--modelo { color: var(--modelo); border-color: rgba(177, 151, 252, 0.35); background: rgba(177, 151, 252, 0.08); }
.chip--caliente { color: var(--caliente); border-color: rgba(247, 185, 85, 0.35); background: rgba(247, 185, 85, 0.08); }

/* ---------- Ficha de un planeta ---------- */
.ficha-cabeza { display: flex; gap: 1.1rem; align-items: center; }
.ficha-cabeza h3 { margin: 0; font-size: 1.55rem; font-weight: 700; letter-spacing: -0.015em; line-height: 1.15;
  color: var(--texto); }
.ficha-sub { margin: 0.2rem 0 0 0; font-size: 0.86rem; color: var(--tenue); }
.datos-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.2rem 1rem; margin: 1.1rem 0 0.4rem 0;
  border-top: 1px solid var(--linea); padding-top: 0.9rem; }
.datos-grid div { padding: 0.35rem 0; display: flex; flex-direction: column; justify-content: space-between; }
.datos-grid dt { font-size: 0.74rem; color: var(--tenue); margin: 0; }
.datos-grid dd { margin: 0.1rem 0 0 0; font-family: var(--mono); font-size: 1.02rem; color: var(--texto); }
.nota { font-size: 0.8rem; color: var(--apagado); margin: 0.4rem 0 0.6rem 0; line-height: 1.5; }

/* ---------- Esferas (aspecto ilustrativo del planeta) ---------- */
.esfera { --tam: 72px; width: var(--tam); height: var(--tam); border-radius: 50%; flex: none; position: relative;
  box-shadow: inset calc(var(--tam) * -0.16) calc(var(--tam) * -0.12) calc(var(--tam) * 0.28) rgba(0, 0, 0, 0.72),
              0 0 calc(var(--tam) * 0.35) var(--brillo, rgba(122, 162, 255, 0.18)); }
.esfera--templado { --brillo: rgba(110, 193, 255, 0.28);
  background: radial-gradient(ellipse 34% 20% at 64% 58%, rgba(84, 178, 120, 0.9), transparent 70%),
              radial-gradient(ellipse 24% 15% at 34% 70%, rgba(84, 178, 120, 0.75), transparent 70%),
              radial-gradient(ellipse 40% 9% at 46% 38%, rgba(255, 255, 255, 0.55), transparent 70%),
              radial-gradient(circle at 32% 30%, #CFEFFF 0%, #5DB2F0 22%, #2766B0 52%, #0F3263 78%, #081428 100%); }
.esfera--helado { --brillo: rgba(200, 230, 255, 0.25);
  background: radial-gradient(ellipse 45% 12% at 50% 40%, rgba(255, 255, 255, 0.5), transparent 70%),
              radial-gradient(circle at 32% 30%, #FFFFFF 0%, #DDF0FB 25%, #9CC6E2 55%, #4C7699 80%, #1C2E44 100%); }
.esfera--desierto { --brillo: rgba(247, 185, 85, 0.25);
  background: radial-gradient(ellipse 50% 10% at 50% 46%, rgba(255, 226, 170, 0.35), transparent 70%),
              radial-gradient(circle at 32% 30%, #FFE7B8 0%, #E9B76A 25%, #B87A3A 55%, #6B3E1D 80%, #2A170B 100%); }
.esfera--lava { --brillo: rgba(255, 110, 60, 0.35);
  background: radial-gradient(ellipse 30% 10% at 58% 56%, rgba(255, 140, 60, 0.95), transparent 70%),
              radial-gradient(ellipse 22% 8% at 34% 40%, rgba(255, 110, 50, 0.85), transparent 70%),
              radial-gradient(circle at 32% 30%, #8A4A3A 0%, #4A2219 35%, #26110C 70%, #120806 100%); }
.esfera--neptuno { --brillo: rgba(111, 211, 242, 0.28);
  background: repeating-linear-gradient(172deg, rgba(255, 255, 255, 0.07) 0 6%, transparent 6% 13%),
              radial-gradient(circle at 32% 30%, #D8F6FF 0%, #77CDEB 24%, #2F8BB8 55%, #134A6E 80%, #08202F 100%); }
.esfera--gigante { --brillo: rgba(247, 185, 85, 0.22);
  background: repeating-linear-gradient(176deg, rgba(120, 72, 40, 0.35) 0 7%, rgba(255, 230, 190, 0.18) 7% 12%, transparent 12% 19%),
              radial-gradient(circle at 32% 30%, #FFF0D6 0%, #E7C08F 26%, #B98955 56%, #6E4A2A 82%, #2B1C10 100%); }

/* ---------- Barras de probabilidad ---------- */
.barra { height: 8px; border-radius: 999px; background: rgba(140, 154, 179, 0.14); overflow: hidden; }
.barra span { display: block; height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, rgba(177, 151, 252, 0.55), var(--modelo)); }

/* ---------- Paneles sin efecto al pasar el mouse ---------- */
[class*="st-key-panel_"] {
  background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio);
  padding: 0.9rem 1rem 0.6rem 1rem; backdrop-filter: blur(10px);
}
.leyenda { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem; font-size: 0.8rem; color: var(--tenue);
  padding: 0 0.3rem 0.4rem 0.3rem; }
.leyenda__escala { width: 120px; height: 6px; border-radius: 999px;
  background: linear-gradient(90deg, #FF5A36, #FF8A4C, #FFC47A, #FFE9C4, #F4F6FF, #AFC6FF); }

/* ---------- Simulador ---------- */
.sim-nombre { margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.015em; color: var(--texto); }
.tamanos { display: flex; align-items: flex-end; gap: 1.6rem; min-height: 120px; margin: 1rem 0 0.6rem 0;
  padding: 0.8rem 1rem; border-radius: 14px; background: rgba(6, 10, 20, 0.55); border: 1px solid var(--linea); }
.tamanos figure { margin: 0; display: flex; flex-direction: column; align-items: center; gap: 0.45rem; }
.tamanos figcaption { font-family: var(--mono); font-size: 0.74rem; color: var(--tenue); }
.veredicto { display: flex; align-items: flex-end; gap: 1rem; margin: 0.2rem 0 0.9rem 0; }
.veredicto__numero { font-family: var(--mono); font-size: clamp(3rem, 2rem + 3vw, 4.4rem); font-weight: 500;
  line-height: 0.95; letter-spacing: -0.04em; color: var(--modelo); text-shadow: 0 0 28px rgba(177, 151, 252, 0.35); }
.veredicto__texto { display: flex; flex-direction: column; gap: 0.15rem; font-size: 0.9rem; color: var(--tenue);
  padding-bottom: 0.35rem; }
.veredicto__texto strong { font-size: 1.25rem; color: var(--texto); font-weight: 600; }
.mini-nombre { margin: 0.7rem 0 0 0; font-weight: 600; font-size: 0.98rem; color: var(--texto); line-height: 1.25; }
.mini-dato { margin: 0.2rem 0 0 0; font-family: var(--mono); font-size: 0.74rem; color: var(--tenue); }
.ficha-cabeza .mini-nombre { margin-top: 0; }

/* ---------- Nuevos descubrimientos ---------- */
.nuevo-prob { display: flex; align-items: baseline; gap: 0.5rem; margin: 1rem 0 0.45rem 0; font-size: 0.82rem;
  color: var(--tenue); }
.nuevo-prob span { font-family: var(--mono); font-size: 1.7rem; font-weight: 500; color: var(--modelo);
  letter-spacing: -0.03em; }

/* ---------- Cómo funciona ---------- */
.flujo { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 0.9rem; margin-top: 2rem; }
.etapa { position: relative; background: var(--superficie); border: 1px solid var(--linea);
  border-top: 2px solid var(--color-etapa, var(--acento)); border-radius: var(--radio); padding: 1.1rem 1rem 1rem 1rem; }
.etapa:not(:last-child)::after { content: ""; position: absolute; top: 2.1rem; right: -0.8rem; width: 0.7rem; height: 1px;
  background: var(--linea-fuerte); }
.etapa__icono { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  color: var(--color-etapa, var(--acento)); background: rgba(255, 255, 255, 0.03); border: 1px solid var(--linea); }
.etapa__icono img { width: 19px; height: 19px; }
.etapa__capa { margin: 0.85rem 0 0.3rem 0; font-weight: 600; font-size: 1.02rem; color: var(--texto); }
.etapa__texto { margin: 0; font-size: 0.82rem; line-height: 1.45; color: var(--tenue); min-height: 3.6em; }
.etapa__dato { margin: 0.8rem 0 0 0; font-family: var(--mono); font-size: 0.8rem; color: var(--color-etapa, var(--acento)); }
.etapa--fuentes { --color-etapa: #9DB8FF; }
.etapa--bronze { --color-etapa: #D9925E; }
.etapa--silver { --color-etapa: #C3CCDD; }
.etapa--gold { --color-etapa: #E9C46A; }
.etapa--modelo { --color-etapa: var(--modelo); }
.etapa--app { --color-etapa: var(--habitable); }
.bloques { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.bloque { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio); padding: 1.2rem; }
.bloque__icono { width: 30px; height: 30px; color: var(--acento); }
.bloque__icono img { width: 26px; height: 26px; }
.bloque h4 { margin: 0.6rem 0 0.4rem 0; font-size: 1.02rem; font-weight: 600; color: var(--texto); }
.bloque p { margin: 0; font-size: 0.86rem; line-height: 1.55; color: var(--tenue); }
.formula { background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio);
  padding: 1.2rem 1.3rem; margin-top: 0.8rem; }
.formula .mono { font-size: 1rem; color: var(--texto); }
.formula p { margin: 0.7rem 0 0 0; font-size: 0.88rem; color: var(--tenue); line-height: 1.55; }
@media (max-width: 1100px) {
  .flujo { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .etapa::after { display: none; }
  .bloques { grid-template-columns: 1fr; }
}
@media (max-width: 640px) { .flujo { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

/* ---------- Widgets ---------- */
[data-testid="stPopover"] button, [data-testid="stBaseButton-secondary"] { backdrop-filter: blur(8px); }
[data-testid="stExpander"] details { background: rgba(13, 21, 38, 0.5); border-color: var(--linea); }
[data-testid="stDataFrame"] { border-radius: var(--radio); overflow: hidden; }

/* ---------- Pie ---------- */
.pie { margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid var(--linea); display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 0.6rem; font-size: 0.8rem; color: var(--apagado); }
.pie a { color: var(--tenue); text-decoration: none; }
.pie a:hover { color: var(--texto); }
"""


def aplicar() -> None:
    """Inyecta la hoja de estilos (se llama una vez por corrida, antes de dibujar la página)."""
    st.html(f"<style>{CSS.replace('__CIELO__', _cielo())}</style>")
