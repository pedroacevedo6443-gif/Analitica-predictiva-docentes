"""Genera el notebook (sin ejecutar). Cada celda lleva metadata {'sec': n} para insertar respuestas después."""
import nbformat as nbf

cells = []
def md(s, sec=None): cells.append((sec, nbf.v4.new_markdown_cell(s)))
def code(s, sec=None): cells.append((sec, nbf.v4.new_code_cell(s)))

md("""# Trabajo Final · Unidad 1 — Diagnóstico y preparación de una serie de tiempo
**Materia:** Series de Tiempo Aplicadas a las Finanzas
**Serie:** Precio de cierre mensual de Rocket Lab USA, Inc. (Nasdaq: RKLB), en USD
**Integrantes:** _(completar nombres del equipo)_
**Fecha de consulta de la fuente:** 2 de octubre de 2026

> Este notebook sigue la estructura de las indicaciones del trabajo final (y de las Actividades 2 y 2-Parte II de Colab). Al final de cada sección hay una celda **«Respuestas»** con las respuestas a las preguntas, basadas en los números calculados arriba.
> El diagnóstico es **descriptivo**: no se prueba formalmente estacionariedad ni se estima ningún modelo. Las pruebas ADF y Ljung-Box se usan solo como apoyo orientativo.""")

# ---------------------------------------------------------------- 1
md("## 1. Identificación y carga de datos", 1)
code('''import os, json, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import statsmodels.api as sm
from statsmodels.tsa.stattools import acf, pacf, adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from IPython.display import display

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({"figure.dpi": 100, "axes.titlesize": 13, "axes.titleweight": "bold"})
C_NIVEL, C_ALT, C_TEST, C_REF = "#1F4E79", "#C55A11", "#2E8B57", "#7F7F7F"

os.makedirs("figuras", exist_ok=True); os.makedirs("tablas", exist_ok=True)
R = {}                      # resultados que consumirá el reporte Word
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
def fmt_fecha(ts):
    ts = pd.Timestamp(ts); return f"{MESES[ts.month-1]}-{ts.year}"
def guarda(fig, nombre):
    fig.tight_layout(); fig.savefig(f"figuras/{nombre}.png", dpi=150, bbox_inches="tight"); plt.show()
def eje_fechas(ax, paso=6):
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]) if paso == 6 else mdates.MonthLocator(interval=paso))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: fmt_fecha(mdates.num2date(x))))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
print("Librerías cargadas")''', 1)
code('''# Carga del archivo. En Google Colab, si el CSV no está en la carpeta, se pide subirlo.
ARCHIVO = "Datos_historicos_RKLB.csv"
if not os.path.exists(ARCHIVO):
    from google.colab import files
    ARCHIVO = list(files.upload().keys())[0]

crudo = pd.read_csv(ARCHIVO, encoding="utf-8-sig")
print("Archivo:", ARCHIVO, "| filas x columnas:", crudo.shape)
print("\\nPrimeras observaciones (tal como vienen en el archivo, orden descendente):")
display(crudo.head())
print("Últimas observaciones del archivo (las más antiguas):")
display(crudo.tail())''', 1)
code('''f = pd.to_datetime(crudo["Fecha"], format="%d.%m.%Y")
ident = pd.DataFrame({
    "Elemento": ["Variable analizada", "Qué representa una observación", "Unidades", "Frecuencia", "Periodo",
                 "Número de observaciones", "Fuente de los datos", "Mercado / emisor", "Fecha de consulta"],
    "Descripción": ["Precio de cierre de la acción de Rocket Lab USA, Inc. (columna «Cierre»)",
                    "Precio de cierre de la acción RKLB al final de un mes de negociación (la fecha es la etiqueta del mes, día 1)",
                    "Dólares estadounidenses por acción (USD)",
                    "Mensual",
                    f"{fmt_fecha(f.min())} a {fmt_fecha(f.max())}",
                    f"{len(crudo)} meses",
                    "Archivo «Datos históricos RKLB» (CSV) proporcionado por el equipo; formato de exportación tipo Investing.com (Fecha, Cierre, Apertura, Máximo, Mínimo, Vol., % var.). Enlace exacto: [completar]",
                    "Nasdaq (ticker RKLB)",
                    "2 de octubre de 2026"]})
ident.to_csv("tablas/t01_identificacion.csv", index=False)
display(ident.style.hide(axis="index"))''', 1)

# ---------------------------------------------------------------- 2
md("## 2. Revisión, limpieza y preparación", 2)
code('''# Conversión de tipos: fecha (dd.mm.aaaa), números, volumen ("23.31M") y % var.
df = crudo.copy()
df["Fecha"] = pd.to_datetime(df["Fecha"], format="%d.%m.%Y")
for c in ["Cierre", "Apertura", "Máximo", "Mínimo"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["Vol_M"] = df["Vol."].str.replace("M", "", regex=False).astype(float)          # millones de acciones negociadas en el mes
df["Var_pct_fuente"] = df["% var."].str.replace("%", "", regex=False).astype(float)  # % var. mensual que reporta la fuente
df = df.drop(columns=["Vol.", "% var."])

print("--- head() (antes de ordenar) ---"); display(df.head())
print("--- info() ---"); df.info()''', 2)
code('''# Valores faltantes y duplicados
nulos = df.isnull().sum()
dup_filas = int(df.duplicated().sum()); dup_fechas = int(df["Fecha"].duplicated().sum())
print("Valores faltantes por columna:"); display(nulos.to_frame("nulos").T)
print("Filas duplicadas completas:", dup_filas, "| Fechas (meses) repetidas:", dup_fechas)

# Orden cronológico ascendente
df = df.sort_values("Fecha").reset_index(drop=True)
print("¿Fechas estrictamente crecientes y únicas?", df["Fecha"].is_monotonic_increasing and df["Fecha"].is_unique)

# Continuidad mensual: ¿falta algún mes entre el primero y el último?
calendario = pd.date_range(df["Fecha"].min(), df["Fecha"].max(), freq="MS")
faltan_meses = calendario.difference(df["Fecha"])
print(f"Meses del calendario en el periodo: {len(calendario)} | meses con dato: {len(df)} | meses faltantes: {len(faltan_meses)}")

# Las fechas son etiquetas «día 1 del mes». ¿Cuántas caen en sábado/domingo? (no son días de negociación, solo identifican el mes)
fin_semana = df[df["Fecha"].dt.dayofweek >= 5]
print(f"Etiquetas de mes que caen en sábado/domingo: {len(fin_semana)} de {len(df)} -> se interpretan como mes, no como día de cotización")
print("¿Algún mes repetido por fin de semana/feriado?", dup_fechas > 0)

# Consistencia interna: % var. de la fuente vs cambio calculado con el cierre (la 1ª fila no tiene previo)
calc = df["Cierre"].pct_change() * 100
dif_max = (calc - df["Var_pct_fuente"]).abs().max()
print(f"Máxima discrepancia entre «% var.» de la fuente y el cambio calculado: {dif_max:.4f} puntos porcentuales")
print("Cierre dentro de [Mínimo, Máximo] en todas las filas:", bool(((df["Cierre"] >= df["Mínimo"]) & (df["Cierre"] <= df["Máximo"])).all()))

# Mes en curso: la última fila (oct-2026) corresponde a un mes incompleto (consulta: 2-oct-2026)
vol_med = df["Vol_M"].iloc[:-1].median()
print(f"\\nÚltima fila: {fmt_fecha(df['Fecha'].iloc[-1])} | volumen {df['Vol_M'].iloc[-1]:.2f} M vs. mediana mensual del resto {vol_med:.1f} M "
      f"({df['Vol_M'].iloc[-1]/vol_med*100:.1f} %) -> mes parcial")

serie = df.set_index("Fecha")["Cierre"].rename("Cierre (USD)")
serie.index.freq = "MS"
R.update(n=len(df), ini=str(df["Fecha"].min().date()), fin=str(df["Fecha"].max().date()), nulos=int(nulos.sum()),
         dup_filas=dup_filas, dup_fechas=dup_fechas, n_finsem=len(fin_semana), n_meses_cal=len(calendario), faltan=len(faltan_meses),
         dif_max_pct=float(dif_max), vol_ult=float(df["Vol_M"].iloc[-1]), vol_med_resto=float(vol_med))
display(df.head())''', 2)
code('''# Decisión sobre el mes parcial: se CONSERVA (es el dato más reciente disponible) y se verifica la sensibilidad más adelante (sección 13).
# Base limpia y ordenada (entregable de datos)
base = df.set_index("Fecha"); base.index.name = "Fecha"
base.round(4).to_csv("RKLB_base_limpia.csv")
print("Base limpia guardada:", base.shape)''', 2)

# ---------------------------------------------------------------- 3
md("## 3. Serie en nivel", 3)
code('''desc = serie.describe().to_frame("Cierre (USD)").T
desc["varianza"] = serie.var(); desc["coef. variación (%)"] = serie.std() / serie.mean() * 100
desc["asimetría"] = serie.skew(); desc["curtosis (exceso)"] = serie.kurt(); desc["rango"] = serie.max() - serie.min()
desc = desc.rename(columns={"count": "n", "mean": "media", "std": "desv. est.", "min": "mínimo", "25%": "Q1", "50%": "mediana", "75%": "Q3", "max": "máximo"})
desc.round(3).to_csv("tablas/t03_descriptiva_nivel.csv"); display(desc.round(3))
imax, imin = serie.idxmax(), serie.idxmin()
print(f"Máximo: {serie.max():.2f} USD en {fmt_fecha(imax)} | Mínimo: {serie.min():.2f} USD en {fmt_fecha(imin)}")
print(f"Primer cierre {serie.iloc[0]:.2f} ({fmt_fecha(serie.index[0])}) -> último {serie.iloc[-1]:.2f} ({fmt_fecha(serie.index[-1])}): {serie.iloc[-1]-serie.iloc[0]:+.2f} USD ({(serie.iloc[-1]/serie.iloc[0]-1)*100:+.1f}%)")
print(f"Caída desde el máximo ({fmt_fecha(imax)}) al último dato: {(serie.iloc[-1]/serie.max()-1)*100:.1f}%")

# Por año calendario: media, desviación y rango (¿la variabilidad es constante?)
por_anio = serie.groupby(serie.index.year).agg(n="size", media="mean", desv_est="std", minimo="min", maximo="max")
por_anio["coef_var_%"] = por_anio["desv_est"] / por_anio["media"] * 100
por_anio.round(2).to_csv("tablas/t03_por_anio.csv"); display(por_anio.round(2))
R["por_anio"] = por_anio.round(2).reset_index().rename(columns={"index": "anio", "Fecha": "anio"}).to_dict("records")''', 3)
code('''# Tendencia: OLS contra el índice de mes (nivel y logaritmo), media móvil 6 meses
t = np.arange(len(serie))
ols = sm.OLS(serie.values, sm.add_constant(t)).fit()
ols_log = sm.OLS(np.log(serie.values), sm.add_constant(t)).fit()
pend, p_pend, r2 = ols.params[1], ols.pvalues[1], ols.rsquared
g_mensual = (np.exp(ols_log.params[1]) - 1) * 100
mm6 = serie.rolling(6).mean()
print(f"Tendencia lineal en nivel: {pend:+.3f} USD/mes (p = {p_pend:.4f}; R² = {r2:.3f})")
print(f"Tendencia lineal en ln(Y): {ols_log.params[1]:+.4f} por mes ≈ {g_mensual:+.2f}% mensual compuesto (R² = {ols_log.rsquared:.3f})")

fig, axs = plt.subplots(1, 2, figsize=(14, 5))
for ax, log in zip(axs, [False, True]):
    ax.plot(serie.index, serie.values, marker="o", ms=4, color=C_NIVEL, label="Cierre mensual RKLB")
    ax.plot(mm6.index, mm6.values, color=C_ALT, lw=2, label="Media móvil 6 meses")
    if not log: ax.plot(serie.index, ols.fittedvalues, color=C_REF, ls="--", label=f"Tendencia lineal ({pend:+.2f} USD/mes)")
    ax.annotate(f"Máx. {serie.max():.1f}", (imax, serie.max()), textcoords="offset points", xytext=(-10, 8), ha="center")
    ax.annotate(f"Mín. {serie.min():.2f}", (imin, serie.min()), textcoords="offset points", xytext=(0, -16), ha="center")
    ax.set(xlabel="Fecha (mes de cotización)", ylabel="Precio de cierre (USD, escala log)" if log else "Precio de cierre (USD por acción)")
    if log: ax.set_yscale("log"); ax.set_ylim(2.8, 260)
    else: ax.set_ylim(-25, 165)
    ax.set_title("Escala logarítmica en Y" if log else "Escala lineal en Y"); eje_fechas(ax); ax.legend(loc="upper left")
fig.suptitle("Rocket Lab (RKLB): precio de cierre mensual en nivel", fontweight="bold"); guarda(fig, "fig_03_nivel")
R.update(media=float(serie.mean()), std=float(serie.std()), mediana=float(serie.median()), minimo=float(serie.min()), maximo=float(serie.max()),
         f_min=str(imin.date()), f_max=str(imax.date()), primero=float(serie.iloc[0]), ultimo=float(serie.iloc[-1]),
         pend=float(pend), p_pend=float(p_pend), r2=float(r2), g_mensual=float(g_mensual), r2_log=float(ols_log.rsquared), cv=float(serie.std()/serie.mean()*100),
         caida_max=float((serie.iloc[-1]/serie.max()-1)*100), asim=float(serie.skew()))''', 3)
code('''# Patrón repetitivo: ¿hay un mes del año sistemáticamente alto o bajo? (exploratorio: solo 3-5 observaciones por mes calendario)
rl = (np.log(serie).diff() * 100)
tmp = pd.DataFrame({"r": rl}); tmp["mes"] = tmp.index.month
est = tmp.groupby("mes")["r"].agg(n="count", media="mean", mediana="median").round(2)
est.index = [MESES[m - 1] for m in est.index]; est.columns = ["n", "cambio log medio (%)", "cambio log mediano (%)"]
est.to_csv("tablas/t03_estacionalidad_mes.csv"); display(est)
print("Meses con cambio medio positivo:", int((est.iloc[:, 1] > 0).sum()), "de 12 | n por mes:", sorted(est["n"].unique().tolist()))
R["est_mes"] = est.reset_index().rename(columns={"index": "mes"}).to_dict("records")''', 3)

# ---------------------------------------------------------------- 4
md("## 4. Primera diferencia  ΔYₜ = Yₜ − Yₜ₋₁", 4)
code('''dif = serie.diff().rename("ΔY (USD)")
t4 = pd.concat([serie, dif], axis=1); t4.index = t4.index.strftime("%Y-%m")
t4.round(2).to_csv("tablas/t04_primera_diferencia.csv"); display(t4.round(2).head(12))
d = dif.dropna()
print(f"Meses con ΔY>0: {(d>0).sum()} | ΔY<0: {(d<0).sum()} | ΔY=0: {(d==0).sum()}")
print(f"Media: {d.mean():+.3f} USD | desv. est.: {d.std():.3f} USD | máx.: {d.max():+.2f} ({fmt_fecha(d.idxmax())}) | mín.: {d.min():+.2f} ({fmt_fecha(d.idxmin())})")
print(f"Desv. est. de ΔY: 1ª mitad {d.iloc[:len(d)//2].std():.2f} USD | 2ª mitad {d.iloc[len(d)//2:].std():.2f} USD")

fig, ax = plt.subplots(figsize=(12, 4.8))
ax.bar(d.index, d.values, color=np.where(d.values >= 0, C_TEST, C_ALT), width=22)
ax.axhline(0, color="k", lw=0.8); ax.axhline(d.mean(), color=C_REF, ls="--", label=f"Media = {d.mean():+.2f} USD")
ax.set(title="Rocket Lab (RKLB): primera diferencia del precio de cierre mensual", xlabel="Fecha (mes de cotización)", ylabel="ΔYₜ = Yₜ − Yₜ₋₁ (USD por acción)")
eje_fechas(ax); ax.legend(); guarda(fig, "fig_04_primera_diferencia")
R.update(d_pos=int((d>0).sum()), d_neg=int((d<0).sum()), d_media=float(d.mean()), d_std=float(d.std()),
         d_max=float(d.max()), f_d_max=str(d.idxmax().date()), d_min=float(d.min()), f_d_min=str(d.idxmin().date()),
         d_std_h1=float(d.iloc[:len(d)//2].std()), d_std_h2=float(d.iloc[len(d)//2:].std()))''', 4)

# ---------------------------------------------------------------- 5
md("## 5. Logaritmo natural  ln(Yₜ)", 5)
code('''positiva = bool((serie > 0).all())
print("¿Todos los cierres son estrictamente positivos?", positiva, f"(mínimo = {serie.min():.2f} USD)")
lnY = np.log(serie).rename("ln(Y)")
t5 = pd.concat([serie, lnY], axis=1); t5.index = t5.index.strftime("%Y-%m")
t5.round(4).to_csv("tablas/t05_log_nivel.csv"); display(t5.round(4).head(10))
print(f"Rango en nivel: {serie.min():.2f}–{serie.max():.2f} USD (el máximo es {serie.max()/serie.min():.1f} veces el mínimo)")
print(f"Rango en logaritmo: {lnY.min():.4f}–{lnY.max():.4f} (amplitud {lnY.max()-lnY.min():.3f} unidades log)")
print(f"Correlación entre Y y ln(Y): {serie.corr(lnY):.4f} (no es 1: el log comprime los valores altos)")
# Dispersión relativa entre mitades: nivel vs log
h = len(serie) // 2
print(f"Desv. est. del nivel: 1ª mitad {serie.iloc[:h].std():.2f} vs 2ª mitad {serie.iloc[h:].std():.2f} (razón {serie.iloc[h:].std()/serie.iloc[:h].std():.1f}x)")
print(f"Desv. est. de ln(Y):  1ª mitad {lnY.iloc[:h].std():.3f} vs 2ª mitad {lnY.iloc[h:].std():.3f} (razón {lnY.iloc[h:].std()/lnY.iloc[:h].std():.1f}x)")
adf_ln = adfuller(lnY, maxlag=4, autolag="AIC")
print(f"ADF sobre ln(Y): estadístico = {adf_ln[0]:.3f}, p = {adf_ln[1]:.3f}  (orientativo)")

fig, axs = plt.subplots(1, 2, figsize=(14, 4.8))
axs[0].plot(serie.index, serie.values, marker="o", ms=3, color=C_NIVEL); axs[0].set(title="Nivel Yₜ", xlabel="Fecha (mes de cotización)", ylabel="Precio de cierre (USD por acción)")
axs[1].plot(lnY.index, lnY.values, marker="o", ms=3, color=C_ALT); axs[1].set(title="Logaritmo natural ln(Yₜ)", xlabel="Fecha (mes de cotización)", ylabel="ln(precio en USD) — sin unidades")
for a in axs: eje_fechas(a)
fig.suptitle("Rocket Lab (RKLB): nivel vs. logaritmo natural del cierre", fontweight="bold"); guarda(fig, "fig_05_log_nivel")
R.update(positiva=positiva, ln_min=float(lnY.min()), ln_max=float(lnY.max()), adf_ln_p=float(adf_ln[1]), adf_ln_stat=float(adf_ln[0]),
         corr_y_ln=float(serie.corr(lnY)), razon_max_min=float(serie.max()/serie.min()),
         std_niv_h1=float(serie.iloc[:h].std()), std_niv_h2=float(serie.iloc[h:].std()), std_ln_h1=float(lnY.iloc[:h].std()), std_ln_h2=float(lnY.iloc[h:].std()))''', 5)

# ---------------------------------------------------------------- 6
md("## 6. Cambio porcentual simple  [(Yₜ − Yₜ₋₁)/Yₜ₋₁] × 100", 6)
code('''pct = (serie.pct_change() * 100).rename("Cambio simple (%)")
t6 = pd.concat([serie, dif, pct], axis=1); t6.index = t6.index.strftime("%Y-%m")
t6.round(3).to_csv("tablas/t06_cambio_simple.csv"); display(t6.round(3).head(10))
print("NaN en la primera observación:", bool(np.isnan(pct.iloc[0])), "| NaN totales:", int(pct.isna().sum()))
p = pct.dropna()
print(f"Positivos: {(p>0).sum()} | negativos: {(p<0).sum()} | media {p.mean():+.2f}% | mediana {p.median():+.2f}% | desv. est. {p.std():.2f}% | máx {p.max():+.2f}% ({fmt_fecha(p.idxmax())}) | mín {p.min():+.2f}% ({fmt_fecha(p.idxmin())})")
# Una misma ΔY en USD implica cambios relativos muy distintos según el nivel de partida
i = p.idxmax(); j = p.idxmin()
print(f"Ej. mayor alza: {fmt_fecha(i)}: {serie.shift(1)[i]:.2f} -> {serie[i]:.2f} USD (ΔY = {dif[i]:+.2f} USD) = {p[i]:+.2f}%")
print(f"Ej. mayor caída: {fmt_fecha(j)}: {serie.shift(1)[j]:.2f} -> {serie[j]:.2f} USD (ΔY = {dif[j]:+.2f} USD) = {p[j]:+.2f}%")
k = d.abs().idxmax(); print(f"Mayor |ΔY|: {fmt_fecha(k)} ({dif[k]:+.2f} USD) = {pct[k]:+.2f}%")
# Comparación: ΔY de magnitud parecida en USD, en 2023 vs 2026
a = dif.abs().loc["2023-01-01":"2023-12-01"].max(); ia = dif.abs().loc["2023-01-01":"2023-12-01"].idxmax()
print(f"Mayor |ΔY| de 2023: {fmt_fecha(ia)} = {dif[ia]:+.2f} USD, pero {pct[ia]:+.2f}%")

fig, ax = plt.subplots(figsize=(12, 4.8))
ax.plot(p.index, p.values, marker="o", ms=4, color=C_NIVEL, label="Cambio porcentual simple")
ax.axhline(0, color="k", lw=0.8); ax.axhline(p.mean(), color=C_REF, ls="--", label=f"Media = {p.mean():+.2f}%")
ax.fill_between(p.index, p.values, 0, where=p.values >= 0, color=C_TEST, alpha=0.2); ax.fill_between(p.index, p.values, 0, where=p.values < 0, color=C_ALT, alpha=0.2)
ax.set(title="Rocket Lab (RKLB): cambio porcentual simple mensual del cierre", xlabel="Fecha (mes de cotización)", ylabel="Cambio porcentual mensual (%)")
eje_fechas(ax); ax.legend(); guarda(fig, "fig_06_cambio_simple")
R.update(p_pos=int((p>0).sum()), p_neg=int((p<0).sum()), p_media=float(p.mean()), p_mediana=float(p.median()), p_std=float(p.std()),
         p_max=float(p.max()), f_p_max=str(i.date()), p_min=float(p.min()), f_p_min=str(j.date()),
         ej_prev=float(serie.shift(1)[i]), ej_act=float(serie[i]), ej_dif=float(dif[i]),
         ej2_prev=float(serie.shift(1)[j]), ej2_act=float(serie[j]), ej2_dif=float(dif[j]),
         k_dif=float(dif[k]), k_pct=float(pct[k]), f_k=str(k.date()), a_dif=float(dif[ia]), a_pct=float(pct[ia]), f_a=str(ia.date()))''', 6)

# ---------------------------------------------------------------- 7
md("## 7. Cambio logarítmico  [ln(Yₜ) − ln(Yₜ₋₁)] × 100", 7)
code('''lr = (lnY.diff() * 100).rename("Cambio log (%)")
lr_alt = (np.log(serie / serie.shift(1)) * 100)
print("Ambas fórmulas coinciden:", bool(np.allclose(lr.dropna(), lr_alt.dropna())))
t7 = pd.concat([serie, pct, lr], axis=1); t7.index = t7.index.strftime("%Y-%m")
t7.round(3).to_csv("tablas/t07_cambio_log.csv"); display(t7.round(3).head(10))
r = lr.dropna(); brecha = (pct - lr).dropna()
print(f"Media {r.mean():+.2f}% | mediana {r.median():+.2f}% | desv. est. {r.std():.2f}% | máx {r.max():+.2f}% ({fmt_fecha(r.idxmax())}) | mín {r.min():+.2f}% ({fmt_fecha(r.idxmin())})")
print(f"Correlación cambio simple vs. logarítmico: {pct.corr(lr):.4f}")
print(f"Diferencia (simple − log): media {brecha.mean():+.2f} pp | mediana {brecha.median():+.2f} pp | máxima en valor absoluto {brecha.abs().max():.2f} pp en {fmt_fecha(brecha.abs().idxmax())}")
peq = p.abs() < 10
print(f"Para |cambio| < 10% ({int(peq.sum())} meses): diferencia máxima {brecha[peq].abs().max():.2f} pp | para |cambio| ≥ 10% ({int((~peq).sum())} meses): {brecha[~peq].abs().max():.2f} pp")
print(f"Suma de cambios log = {r.sum():.2f}%  vs  ln(Y_final/Y_inicial)·100 = {np.log(serie.iloc[-1]/serie.iloc[0])*100:.2f}%  (aditividad)")
print(f"Cambio simple acumulado = {(serie.iloc[-1]/serie.iloc[0]-1)*100:.1f}%  (≠ suma de cambios simples = {p.sum():.1f}%)")
# Simetría: +50% y -50% simples no se compensan; en log sí lo hacen con +x y -x
print(f"Simetría: un +100% simple seguido de -50% simple deja el precio igual (log: {np.log(2)*100:.1f}% y {np.log(0.5)*100:.1f}%)")

fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
axs[0].plot(r.index, r.values, marker="o", ms=4, color=C_ALT, label="Cambio logarítmico"); axs[0].axhline(0, color="k", lw=0.8)
axs[0].axhline(r.mean(), color=C_REF, ls="--", label=f"Media = {r.mean():+.2f}%")
axs[0].set(title="Rocket Lab (RKLB): cambio logarítmico mensual del cierre", ylabel="Cambio logarítmico (% mensual)"); axs[0].legend()
axs[1].plot(p.index, p.values, color=C_NIVEL, label="Cambio simple", lw=2); axs[1].plot(r.index, r.values, color=C_ALT, ls="--", label="Cambio logarítmico", lw=2); axs[1].axhline(0, color="k", lw=0.8)
axs[1].set(title="Cambio simple vs. logarítmico (difieren en los extremos)", xlabel="Fecha (mes de cotización)", ylabel="% mensual"); axs[1].legend()
eje_fechas(axs[1]); guarda(fig, "fig_07_cambio_log")
R.update(r_media=float(r.mean()), r_mediana=float(r.median()), r_std=float(r.std()), r_max=float(r.max()), f_r_max=str(r.idxmax().date()), r_min=float(r.min()), f_r_min=str(r.idxmin().date()),
         r_pos=int((r>0).sum()), r_neg=int((r<0).sum()),
         corr_simple_log=float(pct.corr(lr)), brecha_max=float(brecha.abs().max()), f_brecha_max=str(brecha.abs().idxmax().date()), brecha_media=float(brecha.mean()),
         n_peq=int(peq.sum()), brecha_peq=float(brecha[peq].abs().max()), n_gr=int((~peq).sum()), brecha_gr=float(brecha[~peq].abs().max()),
         suma_log=float(r.sum()), ln_total=float(np.log(serie.iloc[-1]/serie.iloc[0])*100), simple_acum=float((serie.iloc[-1]/serie.iloc[0]-1)*100), suma_simples=float(p.sum()))''', 7)

# ---------------------------------------------------------------- 8
md("## 8. Comparación de transformaciones", 8)
code('''comp = pd.DataFrame({"Nivel (USD)": serie, "1ª diferencia (USD)": dif, "ln(Y)": lnY, "Cambio simple (%)": pct, "Cambio log (%)": lr})
comp_f = comp.copy(); comp_f.index = comp_f.index.strftime("%Y-%m")
comp_f.round(4).to_csv("tablas/t08_comparacion_completa.csv"); display(comp_f.round(3).head(15))

def resumen(x):
    x = x.dropna()
    return pd.Series({"n": len(x), "media": x.mean(), "desv. est.": x.std(), "mín": x.min(), "máx": x.max(), "autocorr. lag 1": x.autocorr(1),
                      "autocorr. lag 6": x.autocorr(6), "p-valor ADF": adfuller(x, maxlag=4, autolag="AIC")[1]})
res = comp.apply(resumen).T.round(3); res.to_csv("tablas/t08_resumen_transformaciones.csv"); display(res)

fig, axs = plt.subplots(5, 1, figsize=(12, 14), sharex=True)
etiquetas = [("Nivel", "USD por acción"), ("Primera diferencia", "USD"), ("Logaritmo natural", "ln(USD)"), ("Cambio simple", "% mensual"), ("Cambio logarítmico", "% mensual")]
for ax, col, (tt, yl) in zip(axs, comp.columns, etiquetas):
    ax.plot(comp.index, comp[col], marker="o", ms=3, color=C_NIVEL if col in comp.columns[:3] else C_ALT); ax.set(title=tt, ylabel=yl)
    if tt not in ("Nivel", "Logaritmo natural"): ax.axhline(0, color="k", lw=0.7)
axs[-1].set_xlabel("Fecha (mes de cotización)"); eje_fechas(axs[-1])
fig.suptitle("Rocket Lab (RKLB): las cinco representaciones de la serie", fontweight="bold", y=1.0); guarda(fig, "fig_08_comparacion")
R["res_transf"] = res.reset_index().rename(columns={"index": "Transformación"}).to_dict("records")''', 8)

# ---------------------------------------------------------------- 9
md("## 9. División Train/Test (cronológica, 80 % / 20 %)", 9)
code('''corte = int(len(serie) * 0.80)
train, test = serie.iloc[:corte], serie.iloc[corte:]
r_tr, r_te = lr.dropna().loc[:train.index[-1]], lr.loc[test.index[0]:]
split = pd.DataFrame({"Conjunto": ["Train", "Test", "Total"], "Observaciones": [len(train), len(test), len(serie)],
                      "% de la muestra": [len(train)/len(serie)*100, len(test)/len(serie)*100, 100.0],
                      "Primer mes": [fmt_fecha(train.index[0]), fmt_fecha(test.index[0]), fmt_fecha(serie.index[0])],
                      "Último mes": [fmt_fecha(train.index[-1]), fmt_fecha(test.index[-1]), fmt_fecha(serie.index[-1])],
                      "Precio medio (USD)": [train.mean(), test.mean(), serie.mean()],
                      "Precio mín–máx (USD)": [f"{train.min():.2f}–{train.max():.2f}", f"{test.min():.2f}–{test.max():.2f}", f"{serie.min():.2f}–{serie.max():.2f}"],
                      "Desv. est. cambio log (%)": [r_tr.std(), r_te.std(), lr.std()]}).round(2)
split.to_csv("tablas/t09_train_test.csv", index=False); display(split.style.hide(axis="index"))
print("Todas las fechas de Train son anteriores a las de Test:", train.index.max() < test.index.min())
print(f"Test: el mínimo ({test.min():.2f}) {'supera' if test.min() > train.max() else 'NO supera'} al máximo de Train ({train.max():.2f}) -> traslape de rangos: {'no' if test.min() > train.max() else 'sí'}")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(train.index, train.values, marker="o", ms=4, color=C_NIVEL, label=f"Train ({len(train)} meses)")
ax.plot(test.index, test.values, marker="o", ms=4, color=C_TEST, label=f"Test ({len(test)} meses)")
lim = train.index[-1] + (test.index[0] - train.index[-1]) / 2
ax.axvline(lim, color="k", ls="--", label=f"Punto de corte (tras {fmt_fecha(train.index[-1])})")
ax.axvspan(lim, test.index[-1] + pd.Timedelta(days=20), color=C_TEST, alpha=0.08)
ax.set(title="Rocket Lab (RKLB): división cronológica Train/Test (80 % / 20 %)", xlabel="Fecha (mes de cotización)", ylabel="Precio de cierre (USD por acción)")
eje_fechas(ax); ax.legend(loc="upper left"); guarda(fig, "fig_09_train_test")
R.update(n_train=len(train), n_test=len(test), tr_ini=str(train.index[0].date()), tr_fin=str(train.index[-1].date()), te_ini=str(test.index[0].date()), te_fin=str(test.index[-1].date()),
         media_train=float(train.mean()), media_test=float(test.mean()), max_train=float(train.max()), min_test=float(test.min()), max_test=float(test.max()), min_train=float(train.min()),
         std_r_train=float(r_tr.std()), std_r_test=float(r_te.std()), traslape=bool(test.min() <= train.max()))''', 9)

# ---------------------------------------------------------------- 10
md("## 10. Rezagos y autocorrelación", 10)
code('''lags = pd.DataFrame({"Mes": serie.index.strftime("%Y-%m"), "Y_t": serie.values, "Lag 1 (Y_t-1)": serie.shift(1).values,
                     "Lag 2 (Y_t-2)": serie.shift(2).values, "Lag 3 (Y_t-3)": serie.shift(3).values}).set_index("Mes")
lags.round(3).to_csv("tablas/t10_rezagos.csv"); display(lags.head(8).round(3))
print("NaN por columna:", lags.isna().sum().to_dict())

filas = []
acf_n = acf(serie, nlags=3, fft=False)
for k in (1, 2, 3):
    par = pd.concat([serie, serie.shift(k)], axis=1).dropna()
    filas.append({"Rezago (meses)": k, "Pares usados": len(par), "Correlación Y_t vs Y_t-k (Pearson)": par.iloc[:, 0].corr(par.iloc[:, 1]), "ACF muestral (statsmodels)": acf_n[k]})
tabla_ac = pd.DataFrame(filas).round(4); tabla_ac.to_csv("tablas/t10_autocorrelaciones_nivel.csv", index=False); display(tabla_ac.style.hide(axis="index"))

acf_r3 = acf(r, nlags=3, fft=False)
tabla_ac_r = pd.DataFrame([{"Rezago (meses)": k, "Correlación (Pearson)": r.autocorr(k), "ACF muestral (statsmodels)": acf_r3[k]} for k in (1, 2, 3)]).round(4)
tabla_ac_r.to_csv("tablas/t10_autocorrelaciones_retorno.csv", index=False); print("Cambio logarítmico:"); display(tabla_ac_r.style.hide(axis="index"))
R.update(ac_nivel=tabla_ac.to_dict("records"), ac_ret=tabla_ac_r.to_dict("records"))''', 10)

# ---------------------------------------------------------------- 11
md("## 11. Correlograma ACF en nivel", 11)
code('''# Con 49 observaciones (48 cambios) se usan 20 rezagos (PACF de statsmodels exige nlags < n/2 = 24). Los rezagos lejanos se estiman con pocos pares: se enfatizan los primeros.
NLAGS = 20
def acf_tabla(x, nlags=NLAGS):
    a, ci = acf(x, nlags=nlags, alpha=0.05, fft=False)
    out = pd.DataFrame({"Rezago": range(nlags + 1), "ACF": a, "Banda inf.": ci[:, 0] - a, "Banda sup.": ci[:, 1] - a})
    out["Fuera de bandas"] = (out["Rezago"] > 0) & (out["ACF"].abs() > out["Banda sup."]); return out.round(3)
def pacf_tabla(x, nlags=NLAGS):
    a, ci = pacf(x, nlags=nlags, alpha=0.05, method="ywm")      # mismo método que plot_pacf(method="ywm")
    out = pd.DataFrame({"Rezago": range(nlags + 1), "PACF": a, "Banda inf.": ci[:, 0] - a, "Banda sup.": ci[:, 1] - a})
    out["Fuera de bandas"] = (out["Rezago"] > 0) & (out["PACF"].abs() > out["Banda sup."]); return out.round(3)

ac_n = acf_tabla(serie); ac_n.to_csv("tablas/t11_acf_nivel.csv", index=False); display(ac_n.style.hide(axis="index"))
fig, ax = plt.subplots(figsize=(11, 4.8))
plot_acf(serie, lags=NLAGS, alpha=0.05, ax=ax, color=C_NIVEL, vlines_kwargs={"colors": C_NIVEL}, title=None)
ax.set(title="Rocket Lab (RKLB): función de autocorrelación (ACF) del precio de cierre en nivel", xlabel="Rezago k (meses)", ylabel="Autocorrelación ρ(k) (adimensional)", ylim=(-1.05, 1.05))
ax.text(0.99, 0.02, "Zona sombreada: banda de confianza al 95 %", transform=ax.transAxes, ha="right", fontsize=9, color=C_REF)
guarda(fig, "fig_11_acf_nivel")
R.update(acf_nivel=ac_n.to_dict("records"), banda_nivel=float(ac_n.loc[1, "Banda sup."]), acf_nivel_fuera=ac_n.loc[ac_n["Fuera de bandas"], "Rezago"].tolist(), NLAGS=NLAGS,
         acf_nivel_pos=int((ac_n.loc[1:, "ACF"] > 0).sum()), acf_nivel_neg=int((ac_n.loc[1:, "ACF"] < 0).sum()))''', 11)

# ---------------------------------------------------------------- 12
md("## 12. Correlograma PACF en nivel", 12)
code('''pa_n = pacf_tabla(serie); pa_n.to_csv("tablas/t12_pacf_nivel.csv", index=False); display(pa_n.style.hide(axis="index"))
fig, ax = plt.subplots(figsize=(11, 4.8))
plot_pacf(serie, lags=NLAGS, alpha=0.05, ax=ax, method="ywm", color=C_ALT, vlines_kwargs={"colors": C_ALT}, title=None)
ax.set(title="Rocket Lab (RKLB): autocorrelación parcial (PACF) del precio de cierre en nivel", xlabel="Rezago k (meses)", ylabel="Autocorrelación parcial φₖₖ (adimensional)", ylim=(-1.05, 1.05))
guarda(fig, "fig_12_pacf_nivel")

cmp_n = pd.DataFrame({"Rezago": range(1, NLAGS + 1), "ACF": ac_n["ACF"][1:].values, "PACF": pa_n["PACF"][1:].values})
cmp_n["|ACF| − |PACF|"] = (cmp_n["ACF"].abs() - cmp_n["PACF"].abs()).round(3); cmp_n.to_csv("tablas/t12_acf_vs_pacf_nivel.csv", index=False); display(cmp_n.head(12).style.hide(axis="index"))
R.update(pacf_nivel=pa_n.to_dict("records"), pacf_nivel_fuera=pa_n.loc[pa_n["Fuera de bandas"], "Rezago"].tolist(), banda_pacf_nivel=float(pa_n.loc[1, "Banda sup."]))''', 12)

# ---------------------------------------------------------------- 13
md("## 13. ACF y PACF de la serie transformada (cambio logarítmico, % mensual)", 13)
code('''ac_r = acf_tabla(r); pa_r = pacf_tabla(r)
ac_r.to_csv("tablas/t13_acf_retorno.csv", index=False); pa_r.to_csv("tablas/t13_pacf_retorno.csv", index=False)
print("ACF del cambio logarítmico:"); display(ac_r.head(13).style.hide(axis="index")); print("PACF del cambio logarítmico:"); display(pa_r.head(13).style.hide(axis="index"))

fig, axs = plt.subplots(2, 2, figsize=(14, 8.5))
plot_acf(serie, lags=NLAGS, ax=axs[0, 0], color=C_NIVEL, vlines_kwargs={"colors": C_NIVEL}, title=None)
plot_pacf(serie, lags=NLAGS, ax=axs[0, 1], method="ywm", color=C_NIVEL, vlines_kwargs={"colors": C_NIVEL}, title=None)
plot_acf(r, lags=NLAGS, ax=axs[1, 0], color=C_ALT, vlines_kwargs={"colors": C_ALT}, title=None)
plot_pacf(r, lags=NLAGS, ax=axs[1, 1], method="ywm", color=C_ALT, vlines_kwargs={"colors": C_ALT}, title=None)
for ax, tt in zip(axs.ravel(), ["ACF · nivel (USD)", "PACF · nivel (USD)", "ACF · cambio logarítmico (%)", "PACF · cambio logarítmico (%)"]):
    ax.set(title=tt, xlabel="Rezago k (meses)", ylabel="Autocorrelación (adimensional)", ylim=(-1.05, 1.05))
fig.suptitle("Rocket Lab (RKLB): correlogramas en nivel vs. cambio logarítmico mensual", fontweight="bold"); guarda(fig, "fig_13_acf_pacf_comparacion")

for nombre, fn, tt, yl in [("fig_13_acf_retorno", plot_acf, "Rocket Lab (RKLB): ACF del cambio logarítmico mensual (%)", "Autocorrelación ρ(k) (adimensional)"),
                           ("fig_13_pacf_retorno", plot_pacf, "Rocket Lab (RKLB): PACF del cambio logarítmico mensual (%)", "Autocorrelación parcial φₖₖ (adimensional)")]:
    fig, ax = plt.subplots(figsize=(11, 4.5)); kw = {"method": "ywm"} if fn is plot_pacf else {}
    fn(r, lags=NLAGS, ax=ax, color=C_ALT, vlines_kwargs={"colors": C_ALT}, title=None, **kw)
    ax.set(title=tt, xlabel="Rezago k (meses)", ylabel=yl, ylim=(-1.05, 1.05)); fig.tight_layout(); fig.savefig(f"figuras/{nombre}.png", dpi=150, bbox_inches="tight"); plt.close(fig)

comp_ac = pd.DataFrame({"Rezago": range(1, NLAGS + 1), "ACF nivel": ac_n["ACF"][1:].values, "ACF cambio log": ac_r["ACF"][1:].values,
                        "PACF nivel": pa_n["PACF"][1:].values, "PACF cambio log": pa_r["PACF"][1:].values}).round(3)
comp_ac.to_csv("tablas/t13_comparacion_acf_pacf.csv", index=False); display(comp_ac.head(12).style.hide(axis="index"))
lb_n = acorr_ljungbox(serie, lags=[10], return_df=True); lb_r = acorr_ljungbox(r, lags=[10], return_df=True)
adf_n = adfuller(serie, maxlag=4, autolag="AIC"); adf_r = adfuller(r, maxlag=4, autolag="AIC")
print(f"Ljung-Box (10 rezagos)  nivel: Q = {lb_n['lb_stat'].iloc[0]:.1f}, p = {lb_n['lb_pvalue'].iloc[0]:.4f} | cambio log: Q = {lb_r['lb_stat'].iloc[0]:.1f}, p = {lb_r['lb_pvalue'].iloc[0]:.3f}")
print(f"ADF (AIC, máx. 4 rezagos)  nivel: p = {adf_n[1]:.3f} | cambio log: p = {adf_r[1]:.4f}   (orientativo; n pequeño)")
print(f"Suma de |ACF| rezagos 1-{NLAGS}: nivel = {comp_ac['ACF nivel'].abs().sum():.2f} | cambio log = {comp_ac['ACF cambio log'].abs().sum():.2f}")
print(f"Rezagos fuera de bandas -> ACF nivel: {ac_n.loc[ac_n['Fuera de bandas'],'Rezago'].tolist()} | PACF nivel: {pa_n.loc[pa_n['Fuera de bandas'],'Rezago'].tolist()} | ACF cambio log: {ac_r.loc[ac_r['Fuera de bandas'],'Rezago'].tolist()} | PACF cambio log: {pa_r.loc[pa_r['Fuera de bandas'],'Rezago'].tolist()}")
R.update(acf_ret=ac_r.to_dict("records"), pacf_ret=pa_r.to_dict("records"), acf_ret_fuera=ac_r.loc[ac_r["Fuera de bandas"], "Rezago"].tolist(), pacf_ret_fuera=pa_r.loc[pa_r["Fuera de bandas"], "Rezago"].tolist(),
         banda_ret=float(ac_r.loc[1, "Banda sup."]), lb_n_p=float(lb_n["lb_pvalue"].iloc[0]), lb_r_p=float(lb_r["lb_pvalue"].iloc[0]), lb_n_q=float(lb_n["lb_stat"].iloc[0]), lb_r_q=float(lb_r["lb_stat"].iloc[0]),
         adf_n_p=float(adf_n[1]), adf_r_p=float(adf_r[1]), sum_abs_n=float(comp_ac["ACF nivel"].abs().sum()), sum_abs_r=float(comp_ac["ACF cambio log"].abs().sum()),
         comp_ac=comp_ac.to_dict("records"))''', 13)
code('''# Chequeos de robustez del diagnóstico: (a) sin el mes parcial oct-2026; (b) solo con Train (lo que se usaría para modelar sin «mirar» Test)
def lag1(x): return x.autocorr(1)
r_sin = r.iloc[:-1]; s_sin = serie.iloc[:-1]
print(f"(a) Sin oct-2026 | autocorr. lag 1 nivel: {lag1(s_sin):.3f} (con: {lag1(serie):.3f}) | cambio log: {lag1(r_sin):.3f} (con: {lag1(r):.3f}) | media cambio log: {r_sin.mean():+.2f}% (con: {r.mean():+.2f}%)")
tr_s = train; tr_r = lr.dropna().loc[:train.index[-1]]
print(f"(b) Solo Train (n={len(tr_s)}) | autocorr. lag 1 nivel: {lag1(tr_s):.3f} | cambio log: {lag1(tr_r):.3f} | ACF cambio log lag 1-3: {np.round(acf(tr_r, nlags=3, fft=False)[1:], 3).tolist()}")
R.update(lag1_nivel_sin=float(lag1(s_sin)), lag1_ret_sin=float(lag1(r_sin)), media_ret_sin=float(r_sin.mean()), lag1_nivel_tr=float(lag1(tr_s)), lag1_ret_tr=float(lag1(tr_r)), lag1_nivel=float(lag1(serie)), lag1_ret=float(lag1(r)))''', 13)

# ---------------------------------------------------------------- 14 (episodios)
md("## 14. Observaciones atípicas, episodios y posibles cambios importantes", 14)
code('''z = (r - r.mean()) / r.std()
mad = (r - r.median()).abs().median() * 1.4826; zr = (r - r.median()) / mad          # z robusto (mediana y MAD)
ep = pd.DataFrame({"Cierre (USD)": serie[r.index], "Cambio simple (%)": pct[r.index], "Cambio log (%)": r, "z": z, "z robusto": zr, "Volumen (M acc.)": df.set_index("Fecha")["Vol_M"][r.index]})
ep_top = ep[(ep["z"].abs() > 1.5)].sort_values("z", key=abs, ascending=False).round(2)
ep_top.index = ep_top.index.strftime("%Y-%m"); ep_top.to_csv("tablas/t14_episodios.csv"); display(ep_top)
print(f"Meses con |z|>2: {int((z.abs()>2).sum())} | |z|>1.5: {int((z.abs()>1.5).sum())} de {len(z)}")

# Rachas de meses consecutivos con el mismo signo
signo = np.sign(r); grupos = (signo != signo.shift()).cumsum()
rachas = r.groupby(grupos).agg(inicio=lambda s: s.index[0], fin=lambda s: s.index[-1], largo="size", signo=lambda s: np.sign(s.iloc[0]), acumulado=lambda s: s.sum())
rachas = rachas.sort_values("largo", ascending=False).head(4)
rachas["inicio"] = rachas["inicio"].map(fmt_fecha); rachas["fin"] = rachas["fin"].map(fmt_fecha); rachas["acumulado"] = rachas["acumulado"].round(1)
display(rachas)

# Volatilidad por año y móvil de 6 meses
vol_anual = r.groupby(r.index.year).agg(n="size", media="mean", desv_est="std", maximo="max", minimo="min").round(2)
vol_anual.to_csv("tablas/t14_volatilidad_anual.csv"); display(vol_anual)
vm = r.rolling(6).std()

fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
axs[0].plot(r.index, r.values, marker="o", ms=4, color=C_ALT, label="Cambio logarítmico mensual")
axs[0].axhline(0, color="k", lw=0.8)
for k_, c_ in [(2, C_REF), (-2, C_REF)]: axs[0].axhline(r.mean() + k_ * r.std(), color=c_, ls="--", lw=1)
axs[0].axhline(r.mean() + 2 * r.std(), color=C_REF, ls="--", lw=1, label="Media ± 2 desv. est.")
for t_, v_ in r[z.abs() > 1.5].items(): axs[0].annotate(fmt_fecha(t_), (t_, v_), textcoords="offset points", xytext=(0, 8 if v_ > 0 else -14), ha="center", fontsize=8)
axs[0].set(title="Rocket Lab (RKLB): cambios logarítmicos mensuales y meses atípicos (|z| > 1.5)", ylabel="Cambio logarítmico (% mensual)", ylim=(-60, 105)); axs[0].legend(loc="upper left")
axs[1].plot(vm.index, vm.values, color=C_NIVEL, lw=2); axs[1].set(title="Volatilidad móvil: desviación estándar de 6 meses del cambio logarítmico", xlabel="Fecha (mes de cotización)", ylabel="Desv. est. (% mensual)")
eje_fechas(axs[1]); guarda(fig, "fig_14_episodios")
R.update(ep=ep_top.reset_index().rename(columns={"index": "Mes", "Fecha": "Mes"}).to_dict("records"), n_z2=int((z.abs()>2).sum()), n_z15=int((z.abs()>1.5).sum()),
         vol_anual=vol_anual.reset_index().rename(columns={"index": "anio", "Fecha": "anio"}).to_dict("records"),
         rachas=rachas.reset_index(drop=True).to_dict("records"), vm_min=float(vm.min()), f_vm_min=str(vm.idxmin().date()), vm_max=float(vm.max()), f_vm_max=str(vm.idxmax().date()))
vol = df.set_index("Fecha")["Vol_M"]
print(f"Volumen mensual: mediana {vol.iloc[:-1].median():.0f} M; mín {vol.iloc[:-1].min():.0f} M ({fmt_fecha(vol.iloc[:-1].idxmin())}); máx {vol.max():.0f} M ({fmt_fecha(vol.idxmax())})")
print(f"Corr(|cambio log|, volumen) sin el mes parcial: {r.iloc[:-1].abs().corr(vol.iloc[1:-1]):.2f}")
R.update(vol_med_total=float(vol.iloc[:-1].median()), vol_max_total=float(vol.max()), f_vol_max=str(vol.idxmax().date()), corr_abs_vol=float(r.iloc[:-1].abs().corr(vol.iloc[1:-1])))''', 14)

# ---------------------------------------------------------------- 15
md("## 15. Conclusión diagnóstica integradora", 15)
code('''R["lag1_nivel_ac"] = R["ac_nivel"][0]
json.dump(R, open("resultados.json", "w"), ensure_ascii=False, indent=1, default=str)
print("Resultados guardados en resultados.json (", len(R), "claves )")''', 15)

if __name__ == "__main__":
    nb = nbf.v4.new_notebook()
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
    for sec, c in cells:
        c.metadata["sec"] = sec
        nb.cells.append(c)
    nbf.write(nb, "RKLB_Trabajo_Final_Unidad1.ipynb")
    print(len(nb.cells), "celdas")
