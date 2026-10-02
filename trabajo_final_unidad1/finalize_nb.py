"""Inserta las celdas de respuestas en el notebook ya ejecutado (no altera código ni salidas)."""
import nbformat as nbf
import respuestas as RS

NB = "RKLB_Trabajo_Final_Unidad1.ipynb"
nb = nbf.read(NB, 4)
# quitar respuestas previas (idempotente)
nb.cells = [c for c in nb.cells if not c.metadata.get("respuestas")]
ult = {}
for i, c in enumerate(nb.cells):
    s = c.metadata.get("sec")
    if s: ult[s] = i
ult[15] = max(i for i, c in enumerate(nb.cells) if c.metadata.get("sec") == 15 and c.cell_type == "markdown")  # conclusión: tras su encabezado

def celda(s):
    txt = "### Respuestas\n\n" + "\n\n".join(f"**{q}**  \n{a}" for q, a in RS.Q[s])
    c = nbf.v4.new_markdown_cell(txt); c.metadata["respuestas"] = True; return c

for s in sorted(ult, reverse=True):
    nb.cells.insert(ult[s] + 1, celda(s))

fuentes = nbf.v4.new_markdown_cell("""---
## Fuentes y archivos
- **Datos:** archivo `Datos_historicos_RKLB.csv` («Datos históricos RKLB», precio mensual de Rocket Lab USA, Inc., Nasdaq: RKLB; oct-2022 a oct-2026), proporcionado por el equipo; consultado el 2 de octubre de 2026. Versión limpia y ordenada: `RKLB_base_limpia.csv`.
- **Indicaciones y rúbrica:** «Trabajo Final · Unidad 1 — Diagnóstico y preparación de una serie de tiempo» y su rúbrica de evaluación; Actividad 2 y Actividad 2-Parte II en Google Colab (Series de Tiempo Aplicadas a las Finanzas).
- **Software:** Python, pandas, NumPy, statsmodels (Seabold & Perktold, 2010), matplotlib, seaborn.""")
fuentes.metadata["respuestas"] = True
nb.cells.append(fuentes)
for c in nb.cells: c.metadata.pop("sec", None)
nbf.write(nb, NB)
print("celdas:", len(nb.cells))
