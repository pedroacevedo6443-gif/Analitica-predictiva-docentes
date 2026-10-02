"""Respuestas a las preguntas de cada sección, calculadas a partir de resultados.json (mismas cifras que el notebook)."""
import json
import numpy as np
import pandas as pd

R = json.load(open("resultados.json"))
base = pd.read_csv("RKLB_base_limpia.csv", parse_dates=["Fecha"]).set_index("Fecha")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
def fm(s): t = pd.Timestamp(s); return f"{MESES[t.month-1]}-{t.year}"
def n1(x): return f"{x:,.1f}"
def n2(x): return f"{x:,.2f}"
def n3(x): return f"{x:.3f}"
def sg2(x): return f"{x:+,.2f}"
def sg1(x): return f"{x:+,.1f}"
A = lambda tabla, k, col: R[tabla][k][col]           # fila k (rezago k) de una tabla ACF/PACF
fin_sem_ej = base.index[base.index.dayofweek >= 5][0]
dia_es = {5: "sábado", 6: "domingo"}[fin_sem_ej.dayofweek]
ep = {e["Mes"]: e for e in R["ep"]}
t_media = R["r_media"] / (R["r_std"] / np.sqrt(R["n"] - 1))
razon_ml = R["max_test"] / R["max_train"]
ruido = 20 * 0.7979 / np.sqrt(R["n"] - 1)             # suma esperada de |ACF| en 20 rezagos bajo ruido blanco
va = {v["anio"]: v for v in R["vol_anual"]}
pa = {v["anio"]: v for v in R["por_anio"]}
rach = R["rachas"]

Q = {}
Q[1] = [
 ("¿Qué variable analizan y qué representa una observación?",
  f"La variable es el **precio de cierre de la acción de Rocket Lab USA, Inc. (Nasdaq: RKLB)**. Cada observación es el precio al que cerró la acción al final de un mes de negociación; la columna «Fecha» (día 1 de cada mes) funciona como etiqueta del mes. La base tiene {R['n']} observaciones."),
 ("¿En qué unidades se expresa?",
  "En dólares estadounidenses (USD) por acción."),
 ("¿Cuál es la fuente, periodo y frecuencia?",
  f"La fuente es el archivo CSV «Datos históricos RKLB» proporcionado por el equipo (con el formato de exportación tipo Investing.com: Fecha, Cierre, Apertura, Máximo, Mínimo, Vol., % var.); el enlace exacto debe completarse en el reporte. El periodo va de **{fm(R['ini'])} a {fm(R['fin'])}**, con **frecuencia mensual**. La fecha de consulta es el 2 de octubre de 2026; por eso la última observación ({fm(R['fin'])}) corresponde a un mes todavía incompleto."),
]
Q[2] = [
 ("¿Existen faltantes o duplicados?",
  f"No. Hay {R['nulos']} valores faltantes en las 7 columnas, {R['dup_filas']} filas duplicadas y {R['dup_fechas']} meses repetidos. Además, el «% var.» que reporta la fuente coincide con el cambio porcentual calculado a partir del cierre (discrepancia máxima de {R['dif_max_pct']:.4f} puntos porcentuales, solo por redondeo) y el cierre está siempre entre el mínimo y el máximo del mes."),
 ("¿Qué decisión tomaron y por qué?",
  f"(1) Convertir «Fecha» (formato dd.mm.aaaa) a *datetime* y **ordenar de forma ascendente**, porque el archivo venía del más reciente al más antiguo y los rezagos y diferencias requieren orden cronológico. (2) Convertir «Vol.» (por ejemplo «23.31M») y «% var.» a números. (3) **No imputar ni eliminar nada**, porque no hay faltantes ni duplicados. (4) **Conservar {fm(R['fin'])}** aunque sea un mes parcial (su volumen es de {n2(R['vol_ult'])} M de acciones, solo {R['vol_ult']/R['vol_med_resto']*100:.1f} % de la mediana mensual de {n1(R['vol_med_resto'])} M), por ser el dato más reciente; se verificó que no cambia el diagnóstico: la autocorrelación de rezago 1 del cambio logarítmico es {n3(R['lag1_ret_sin'])} sin ese mes y {n3(R['lag1_ret'])} con él."),
 ("¿Hay observaciones repetidas por fines de semana o días no hábiles?",
  f"No. Los {R['n']} meses del calendario entre {fm(R['ini'])} y {fm(R['fin'])} tienen exactamente un dato (0 meses faltantes y 0 repetidos). Como la serie es mensual, la fecha es solo la etiqueta del mes (día 1): {R['n_finsem']} de las {R['n']} etiquetas caen en sábado o domingo (por ejemplo, {fin_sem_ej.strftime('%d')}-{MESES[fin_sem_ej.month-1]}-{fin_sem_ej.year} fue {dia_es}), pero eso no genera repeticiones ni huecos, porque el dato es el precio de cierre del mes y no el de ese día."),
]
Q[3] = [
 ("¿Se observa tendencia?",
  f"Sí, una **tendencia creciente muy marcada pero no monótona**. El precio pasó de {n2(R['primero'])} USD ({fm(R['ini'])}) a {n2(R['ultimo'])} USD ({fm(R['fin'])}), un aumento de {R['simple_acum']:,.0f} %. La recta de tendencia suma {n2(R['pend'])} USD por mes (p < 0.001; R² = {n3(R['r2'])}), y en logaritmos el crecimiento equivale a {n1(R['g_mensual'])} % mensual compuesto (R² = {n3(R['r2_log'])}), es decir, la trayectoria es más exponencial que lineal. De {fm(R['ini'])} a mediados de 2024 el precio estuvo plano entre 3.76 y 7.37 USD; desde nov-2024 despegó, alcanzó el máximo de **{n2(R['maximo'])} USD en {fm(R['f_max'])}** y después cayó {abs(R['caida_max']):.1f} % hasta el último dato."),
 ("¿Hay algún patrón repetitivo?",
  f"No hay una estacionalidad clara. Lo que se repite son **ciclos de auge y corrección**: una racha de {rach[0]['largo']} alzas mensuales consecutivas entre {rach[0]['inicio']} y {rach[0]['fin']} (cambio logarítmico acumulado de {n1(rach[0]['acumulado'])} %), otra de {rach[1]['largo']} alzas entre {rach[1]['inicio']} y {rach[1]['fin']} ({n1(rach[1]['acumulado'])} %), seguidas de caídas. Por mes calendario, 10 de 12 meses tienen cambio promedio positivo (reflejo de la tendencia); solo febrero (−16.3 %) y marzo (−10.7 %) tienen media y mediana negativas, pero hay apenas 4 observaciones por mes y la desviación mensual es de {n1(R['r_std'])} %, así que no se puede afirmar un patrón estacional."),
 ("¿La variabilidad parece constante?",
  f"No. La desviación estándar del precio crece año con año: {n2(pa[2022]['desv_est'])} USD (2022), {n2(pa[2023]['desv_est'])} (2023), {n2(pa[2024]['desv_est'])} (2024), {n2(pa[2025]['desv_est'])} (2025) y {n2(pa[2026]['desv_est'])} (2026). La primera mitad de la muestra tiene desviación de {n2(R['std_niv_h1'])} USD y la segunda de {n2(R['std_niv_h2'])} USD (**{R['std_niv_h2']/R['std_niv_h1']:.1f} veces mayor**). La variabilidad aumenta junto con el nivel (heterocedasticidad), por lo que en el panel de escala logarítmica las oscilaciones se ven más parejas que en la escala lineal."),
 ("¿Qué periodos llaman particularmente la atención?",
  f"(1) **nov-2024**: el precio pasó de 10.70 a 27.28 USD en un solo mes (+154.95 %), el mayor salto de la muestra y el inicio de un nuevo rango de precios (desde entonces nunca volvió por debajo de 17.88 USD). (2) **dic-2025 y may-2026**: alzas de +65.5 % y +73.9 %, esta última hasta el máximo de {n2(R['maximo'])} USD. (3) **jun-2026 y jul-2026**: caídas de −29.2 % y −36.1 % (de 143.48 a 64.95 USD en dos meses). (4) **sep-2023**: caída de −30.6 % cuando el precio era de solo 4–6 USD. (5) El mínimo de {n2(R['minimo'])} USD en {fm(R['f_min'])}."),
]
Q[4] = [
 ("¿Qué significa una diferencia positiva y una negativa?",
  f"ΔY > 0 significa que la acción **cerró el mes más alta que el mes anterior** ({R['d_pos']} de {R['d_pos']+R['d_neg']} meses; el mayor aumento fue {sg2(R['d_max'])} USD en {fm(R['f_d_max'])}). ΔY < 0 significa que cerró **más baja** ({R['d_neg']} meses; la mayor caída fue {sg2(R['d_min'])} USD en {fm(R['f_d_min'])})."),
 ("¿En qué unidades se interpreta?",
  "En **USD por acción por mes**, las mismas unidades que el nivel: ΔY = +60.97 significa que el precio subió 60.97 dólares respecto al mes previo."),
 ("¿Qué cambia respecto del nivel?",
  f"La serie deja de describir «cuánto vale» y pasa a describir «cuánto cambió». **Desaparece la tendencia**: el nivel tiene media de {n2(R['media'])} USD y autocorrelación de rezago 1 de 0.906, mientras que ΔY oscila alrededor de {sg2(R['d_media'])} USD con autocorrelación de rezago 1 de −0.060. Pero **no se corrige la variabilidad**: la desviación de ΔY es de {n2(R['d_std_h1'])} USD en la primera mitad y de {n2(R['d_std_h2'])} USD en la segunda, porque los saltos en dólares crecen con el precio."),
]
Q[5] = [
 ("¿Es válido aplicar logaritmo a su serie?",
  f"Sí. El logaritmo exige valores estrictamente positivos y el cierre mínimo de RKLB es de {n2(R['minimo'])} USD (los 49 cierres son > 0). Un precio accionario además no puede ser cero o negativo."),
 ("¿Qué efecto tiene sobre la escala?",
  f"Comprime los valores altos y expande los bajos: el máximo es {R['razon_max_min']:.1f} veces el mínimo en nivel, pero en ln la amplitud es de {n2(R['ln_max']-R['ln_min'])} unidades (de {n2(R['ln_min'])} a {n2(R['ln_max'])}). El crecimiento casi exponencial se vuelve más lineal (R² de la tendencia: {n3(R['r2'])} en nivel vs {n3(R['r2_log'])} en ln) y la desproporción de variabilidad entre mitades baja de {R['std_niv_h2']/R['std_niv_h1']:.1f} veces en nivel a {R['std_ln_h2']/R['std_ln_h1']:.1f} veces en ln. Además, las diferencias en ln son variaciones relativas."),
 ("¿El logaritmo garantiza estacionariedad? Expliquen.",
  f"**No.** El logaritmo solo es una transformación de escala monótona: no elimina la tendencia ni el nivel cambiante. ln(Y) sube de {n2(R['ln_min'])} a {n2(R['ln_max'])} y mantiene una autocorrelación de rezago 1 de 0.977 (incluso mayor que la del nivel, 0.906); la prueba ADF, usada solo como apoyo orientativo, da p = {n3(R['adf_ln_p'])}, sin evidencia contra una raíz unitaria. Además, la variabilidad de ln(Y) sigue siendo {R['std_ln_h2']/R['std_ln_h1']:.1f} veces mayor en la segunda mitad. Para quitar la tendencia hay que diferenciar (por ejemplo, tomar el cambio logarítmico)."),
]
Q[6] = [
 ("¿Cómo interpretan valores positivos y negativos?",
  f"Un valor positivo es un **aumento porcentual** del precio respecto al mes anterior; uno negativo, una **disminución porcentual**. Hubo {R['p_pos']} meses positivos y {R['p_neg']} negativos; el cambio promedio es de {sg2(R['p_media'])} % (mediana {sg2(R['p_mediana'])} %) con desviación de {n2(R['p_std'])} %. Por ejemplo, +154.95 % en {fm(R['f_p_max'])} significa que el precio de {n2(R['ej_prev'])} USD se multiplicó por 2.55 hasta {n2(R['ej_act'])} USD, y {sg2(R['p_min'])} % en {fm(R['f_p_min'])} significa que bajó de {n2(R['ej2_prev'])} a {n2(R['ej2_act'])} USD."),
 ("¿Por qué aparece NaN en la primera observación?",
  f"Porque la fórmula necesita Y(t−1) y para {fm(R['ini'])}, el primer mes de la muestra, no existe un mes previo en la base; el cálculo es indefinido. Se tiene 1 NaN, por lo que quedan {R['n']-1} cambios porcentuales. No se imputa."),
 ("¿Qué diferencia existe respecto de la primera diferencia?",
  f"La primera diferencia es **absoluta** (USD) y depende del nivel de precio; el cambio simple es **relativo** (% del precio previo) y no tiene unidades. Ejemplos de RKLB: en {fm(R['f_a'])} el precio cayó solo {abs(R['a_dif']):.2f} USD, pero eso fue {R['a_pct']:.2f} %; en {fm(R['f_k'])} la mayor variación en dólares ({sg2(R['k_dif'])} USD) fue {sg2(R['k_pct'])} %; en cambio, el mayor cambio relativo ({sg2(R['p_max'])} %, {fm(R['f_p_max'])}) solo representó {sg2(R['ej_dif'])} USD. Con ΔY, los meses de 2026 parecen enormes y los de 2023 insignificantes; con el cambio porcentual son comparables."),
]
Q[7] = [
 ("¿Cómo se interpreta el signo?",
  f"Positivo: el logaritmo del precio subió, o sea, el precio **aumentó** respecto al mes anterior ({R['r_pos']} meses); negativo: el precio **disminuyó** ({R['r_neg']} meses). La magnitud, multiplicada por 100, es una variación porcentual continua: {sg2(R['r_max'])} % en {fm(R['f_r_max'])} equivale a multiplicar el precio por e^0.936 = 2.55, y {sg2(R['r_min'])} % en {fm(R['f_r_min'])} a multiplicarlo por e^−0.448 = 0.64."),
 ("¿Qué tan parecido es al cambio porcentual simple?",
  f"Muy parecido cuando el cambio es pequeño y distinto cuando es grande. En toda la muestra la correlación entre ambos es de {R['corr_simple_log']:.4f}. En los {R['n_peq']} meses con |cambio| < 10 %, la diferencia máxima es de apenas {R['brecha_peq']:.2f} puntos porcentuales; en los {R['n_gr']} meses con |cambio| ≥ 10 % llega a {R['brecha_gr']:.2f} puntos (en {fm(R['f_brecha_max'])}: +154.95 % simple vs +93.59 % logarítmico). Como RKLB se mueve en promedio {n1(R['p_std'])} % por mes, la diferencia es relevante: el cambio promedio es de {n2(R['p_media'])} % en simple y de {n2(R['r_media'])} % en logarítmico."),
 ("¿Qué ventaja presenta para estudiar cambios a través del tiempo?",
  f"(1) **Es aditivo en el tiempo**: la suma de los {R['n']-1} cambios logarítmicos ({n2(R['suma_log'])} %) es exactamente ln(Y final / Y inicial)·100; con cambios simples no funciona (su suma es {n1(R['suma_simples'])} % y el cambio acumulado real es {R['simple_acum']:,.1f} %). (2) Es **simétrico**: +100 % y −50 % simples dejan el precio igual, mientras que en logaritmos son +69.3 % y −69.3 %. (3) No está acotado por −100 % y su distribución es menos asimétrica (media {n2(R['r_media'])} % y mediana {n2(R['r_mediana'])} %, frente a {n2(R['p_media'])} % y {n2(R['p_mediana'])} % en simple)."),
]
rt = {r["Transformación"]: r for r in R["res_transf"]}
Q[8] = [
 ("¿Qué información conserva cada transformación?",
  f"**Nivel**: el valor en USD, incluida la tendencia (autocorr. rezago 1 = {rt['Nivel (USD)']['autocorr. lag 1']:.3f}). **1ª diferencia**: el cambio absoluto en USD; sin tendencia pero dependiente de la escala. **ln(Y)**: la forma completa del nivel en escala relativa (autocorr. rezago 1 = {rt['ln(Y)']['autocorr. lag 1']:.3f}). **Cambio simple**: la variación relativa (%) mes a mes, asimétrica (de {n1(rt['Cambio simple (%)']['mín'])} % a {n1(rt['Cambio simple (%)']['máx'])} %). **Cambio logarítmico**: la variación relativa continua (%), aditiva y más simétrica (de {n1(rt['Cambio log (%)']['mín'])} % a {n1(rt['Cambio log (%)']['máx'])} %). Las tres últimas transformaciones pierden el nivel absoluto del precio."),
 ("¿Cuál facilita los cambios relativos?",
  "El **cambio porcentual simple** y el **cambio logarítmico**, porque expresan cada variación como proporción del precio previo. El logarítmico es el más conveniente para el análisis temporal (aditividad y simetría); el simple es el más directo para comunicar un rendimiento mensual."),
 ("¿Cuál parece reducir más la tendencia o persistencia visual?",
  f"El **cambio logarítmico** y el **cambio simple**: sus gráficas oscilan alrededor de cero sin tendencia y sus autocorrelaciones de rezago 1 son {rt['Cambio log (%)']['autocorr. lag 1']:.3f} y {rt['Cambio simple (%)']['autocorr. lag 1']:.3f} (frente a 0.906 del nivel y 0.977 de ln). La primera diferencia también elimina la tendencia, pero sus oscilaciones crecen con el tiempo (desv. de {n2(R['d_std_h1'])} USD a {n2(R['d_std_h2'])} USD). ln(Y) conserva casi toda la persistencia."),
]
Q[9] = [
 ("¿Cuántas observaciones quedaron en cada conjunto?",
  f"**Train: {R['n_train']} observaciones ({R['n_train']/R['n']*100:.1f} %)** y **Test: {R['n_test']} observaciones ({R['n_test']/R['n']*100:.1f} %)**, de un total de {R['n']} (corte = int(49 × 0.80) = 39)."),
 ("¿Qué fechas comprende cada uno?",
  f"Train: de **{fm(R['tr_ini'])} a {fm(R['tr_fin'])}**. Test: de **{fm(R['te_ini'])} a {fm(R['te_fin'])}** (incluye el mes parcial {fm(R['fin'])}). Todo Train es anterior a Test."),
 ("¿Por qué no se utiliza una división aleatoria?",
  f"Porque en una serie de tiempo el orden contiene la información. Una división aleatoria (1) **filtraría información del futuro** al entrenamiento: se estimaría con meses de 2026 para «pronosticar» meses de 2025; (2) **rompería la dependencia temporal** que los rezagos y el ACF necesitan (la autocorrelación de rezago 1 es de {n3(A('acf_nivel',1,'ACF'))}); y (3) no imita el uso real, que es predecir un futuro todavía no observado. En RKLB el efecto sería grave: el precio medio es de {n2(R['media_train'])} USD en Train y de {n2(R['media_test'])} USD en Test, y el máximo de Test ({n2(R['max_test'])} USD) es {razon_ml:.1f} veces el de Train ({n2(R['max_train'])} USD); mezclar ambos regímenes subestimaría artificialmente el error de pronóstico."),
 ("¿Para qué servirá Test posteriormente?",
  f"Para evaluar **fuera de muestra** los pronósticos de los modelos estimados únicamente con Train (comparar lo pronosticado contra lo observado de {fm(R['te_ini'])} a {fm(R['te_fin'])}), comparar modelos y detectar sobreajuste. No debe usarse para elegir transformaciones ni parámetros. Como solo tiene {R['n_test']} meses y el último es parcial, la evaluación tendrá poca potencia; y en nivel el Test queda casi totalmente fuera del rango visto en Train (mínimo de Test {n2(R['min_test'])} USD vs máximo de Train {n2(R['max_train'])} USD), mientras que en cambios logarítmicos las desviaciones son comparables ({n1(R['std_r_train'])} % en Train y {n1(R['std_r_test'])} % en Test)."),
]
Q[10] = [
 ("¿Qué representa cada rezago según la frecuencia de la serie?",
  "Como la serie es mensual, **Lag 1** es el precio de cierre del mes anterior, **Lag 2** el de hace dos meses y **Lag 3** el de hace tres meses (por ejemplo, para jun-2026 los rezagos son may-2026, abr-2026 y mar-2026)."),
 ("¿Por qué aparecen NaN?",
  f"Porque para los primeros meses no existe el pasado requerido: el primer mes ({fm(R['ini'])}) no tiene Lag 1; los dos primeros no tienen Lag 2 y los tres primeros no tienen Lag 3. Resultan 1, 2 y 3 NaN, y por eso las correlaciones se calculan con {R['ac_nivel'][0]['Pares usados']}, {R['ac_nivel'][1]['Pares usados']} y {R['ac_nivel'][2]['Pares usados']} pares completos."),
 ("¿Qué rezago presenta mayor autocorrelación?",
  f"En nivel, el **rezago 1**: {n3(R['ac_nivel'][0]['Correlación Y_t vs Y_t-k (Pearson)'])} (Pearson; ACF muestral {n3(R['ac_nivel'][0]['ACF muestral (statsmodels)'])}), seguido del rezago 2 ({n3(R['ac_nivel'][1]['Correlación Y_t vs Y_t-k (Pearson)'])}) y el rezago 3 ({n3(R['ac_nivel'][2]['Correlación Y_t vs Y_t-k (Pearson)'])}). En el cambio logarítmico las tres son pequeñas y la de mayor magnitud es el rezago 3 ({n3(R['ac_ret'][2]['Correlación (Pearson)'])})."),
 ("¿Cómo interpretan signo y magnitud?",
  f"Son **coeficientes de correlación** (adimensionales, entre −1 y 1), no porcentajes de cambio ni porcentaje explicado: 0.906 **no** significa que el precio suba 90.6 % ni que el mes anterior «explique» 90.6 % del actual. El signo positivo indica que un mes con precio alto suele ir seguido de otro con precio alto (y viceversa); la magnitud grande y decreciente (0.906, 0.819, 0.806) indica **fuerte persistencia del nivel**, consecuencia de la tendencia. En el cambio logarítmico ({n3(R['ac_ret'][0]['Correlación (Pearson)'])}, {n3(R['ac_ret'][1]['Correlación (Pearson)'])}, {n3(R['ac_ret'][2]['Correlación (Pearson)'])}) las magnitudes son cercanas a cero: el cambio de un mes casi no se relaciona linealmente con los de los tres meses previos. La pequeña diferencia entre Pearson y ACF se debe a que la ACF usa la media y la varianza de toda la muestra."),
]
Q[11] = [
 ("¿Qué representa cada barra?",
  "Cada barra es la autocorrelación muestral ρ(k) entre el precio de un mes y el de k meses antes (k en el eje horizontal). La altura indica magnitud y dirección; la zona sombreada es la banda de confianza al 95 % alrededor de cero."),
 ("¿Qué rezagos sobrepasan las bandas?",
  f"Los **rezagos 1, 2, 3 y 4** ({n3(A('acf_nivel',1,'ACF'))}, {n3(A('acf_nivel',2,'ACF'))}, {n3(A('acf_nivel',3,'ACF'))} y {n3(A('acf_nivel',4,'ACF'))}; la banda va de ±{n3(R['banda_nivel'])} en el rezago 1 a ±{n3(A('acf_nivel',4,'Banda sup.'))} en el 4). Desde el rezago 5 ({n3(A('acf_nivel',5,'ACF'))}) las barras quedan dentro porque las bandas se ensanchan (±{n3(A('acf_nivel',5,'Banda sup.'))})."),
 ("¿Predominan autocorrelaciones positivas o negativas?",
  f"Positivas: {R['acf_nivel_pos']} de los {R['NLAGS']} rezagos son positivos (rezagos 1 a 15) y las negativas aparecen solo del 16 al 20 y son pequeñas (entre {n3(A('acf_nivel',16,'ACF'))} y {n3(A('acf_nivel',20,'ACF'))})."),
 ("¿Disminuyen conforme aumenta el rezago?",
  f"Sí, pero **lentamente**: {n3(A('acf_nivel',1,'ACF'))} (rezago 1), {n3(A('acf_nivel',6,'ACF'))} (rezago 6), {n3(A('acf_nivel',10,'ACF'))} (rezago 10), {n3(A('acf_nivel',12,'ACF'))} (rezago 12) y cerca de cero en el rezago 15 ({n3(A('acf_nivel',15,'ACF'))})."),
 ("¿Qué patrón general observan?",
  f"Un **decaimiento lento y suave desde valores muy altos**, típico de una serie con tendencia y nivel cambiante (no estacionaria en nivel): la persistencia es alta. La prueba de Ljung-Box con 10 rezagos lo confirma (Q = {n1(R['lb_n_q'])}, p < 0.0001)."),
 ("¿Qué significa que una barra quede dentro de las bandas?",
  f"Que esa autocorrelación **no se distingue estadísticamente de cero** al 95 %; no demuestra que sea cero. Con solo {R['n']} observaciones las bandas son anchas (±{n3(R['banda_nivel'])} a ±0.83), por lo que hay poca potencia, sobre todo en los rezagos lejanos, que se calculan con pocos pares."),
]
Q[12] = [
 ("¿Qué rezagos destacan?",
  f"Fuera de las bandas (±{n3(R['banda_pacf_nivel'])}) quedan el **rezago 1** ({n3(A('pacf_nivel',1,'PACF'))}, de lejos el dominante), el rezago 3 ({n3(A('pacf_nivel',3,'PACF'))}, apenas fuera) y el rezago 6 ({n3(A('pacf_nivel',6,'PACF'))}, negativo)."),
 ("¿Coinciden con ACF?",
  f"Solo en parte. La ACF tiene fuera de bandas los rezagos 1 a 4; la PACF, los rezagos 1, 3 y 6. Coinciden en el rezago 1, que es el fundamental. Los rezagos 2 y 4 destacan en la ACF pero no en la PACF."),
 ("¿Existe ACF alta pero PACF considerablemente menor?",
  f"Sí. Rezago 2: ACF {n3(A('acf_nivel',2,'ACF'))} vs PACF {n3(A('pacf_nivel',2,'PACF'))}; rezago 4: {n3(A('acf_nivel',4,'ACF'))} vs {n3(A('pacf_nivel',4,'PACF'))}; rezago 3: {n3(A('acf_nivel',3,'ACF'))} vs {n3(A('pacf_nivel',3,'PACF'))}."),
 ("¿Cómo interpretan ese caso?",
  f"La ACF mide la asociación total y arrastra el efecto en cadena: como cada precio depende del anterior, el de hace 2 o 4 meses parece relacionado con el actual aunque solo lo esté a través del mes inmediato. Al controlar los rezagos intermedios, la relación **directa** con el precio de hace 2 meses es prácticamente nula ({n3(A('pacf_nivel',2,'PACF'))}). La persistencia temporal de RKLB se concentra en el mes anterior. Los rezagos 3 y 6 de la PACF son marginales: al evaluar 20 rezagos al 5 % se espera ≈ 1 «falso positivo», por lo que no se interpretan como ciclos reales."),
 ("¿Qué información adicional aporta PACF?",
  "Separa la dependencia **directa** de la acumulada. Aquí sugiere que casi toda la dependencia del nivel es de primer orden con coeficiente cercano a 1, comportamiento parecido a una caminata aleatoria, lo que es una pista para el modelado futuro y no un modelo estimado."),
]
Q[13] = [
 ("¿La dependencia temporal se ve igual que en nivel?",
  f"No. En nivel la ACF es {n3(A('acf_nivel',1,'ACF'))} en el rezago 1 y decae lentamente; en el cambio logarítmico es {n3(A('acf_ret',1,'ACF'))} en el rezago 1 y las barras son pequeñas y de signo alternante, sin forma. La PACF del nivel tiene una barra dominante ({n3(A('pacf_nivel',1,'PACF'))}); la del cambio logarítmico no tiene ninguna."),
 ("¿En cuál hay mayor persistencia?",
  f"En el **nivel**. La suma de |ACF| en los {R['NLAGS']} rezagos es de {n2(R['sum_abs_n'])} en nivel y de {n2(R['sum_abs_r'])} en cambio logarítmico, valor similar al ≈ {n2(ruido)} que se esperaría de ruido blanco con {R['n']-1} datos. Ljung-Box (10 rezagos): p < 0.0001 en nivel y p = {n3(R['lb_r_p'])} en cambio logarítmico."),
 ("¿Cambian las barras que superan las bandas?",
  f"Sí. En nivel superan las bandas los rezagos 1–4 (ACF) y 1, 3 y 6 (PACF); en el cambio logarítmico **ninguna barra** supera las bandas (±{n3(R['banda_ret'])}), ni en ACF ni en PACF. Las más cercanas son el rezago 11 (ACF {n3(A('acf_ret',11,'ACF'))}; PACF {n3(A('pacf_ret',11,'PACF'))}) y el 12 (ACF {n3(A('acf_ret',12,'ACF'))}; PACF {n3(A('pacf_ret',12,'PACF'))}), que sugerirían algo anual, pero quedan dentro y no se pueden distinguir de ruido."),
 ("¿Qué cambia en el patrón general?",
  "Se pasa de un decaimiento lento desde 0.885, con persistencia fuerte, a un patrón de ruido blanco aparente: autocorrelaciones pequeñas alrededor de cero, sin decaimiento ni cortes definidos. Esto es consistente con que el logaritmo del precio se comporte como una caminata aleatoria, aunque el correlograma por sí solo no lo prueba. Los resultados casi no cambian si se excluye el mes parcial (autocorr. rezago 1 de "
  f"{n3(R['lag1_ret_sin'])}) o si se usa solo Train (nivel {n3(R['lag1_nivel_tr'])}; cambio logarítmico {n3(R['lag1_ret_tr'])})."),
 ("¿El correlograma por sí solo permite afirmar estacionariedad?",
  f"**No.** (1) El correlograma solo mide dependencia lineal; la estacionariedad también exige media y varianza constantes en el tiempo. (2) En el cambio logarítmico la ACF es casi nula, pero la volatilidad no es constante: su desviación móvil de 6 meses va de {n1(R['vm_min'])} % ({fm(R['f_vm_min'])}) a {n1(R['vm_max'])} % ({fm(R['f_vm_max'])}), y por año de {n1(va[2023]['desv_est'])} % a {n1(va[2024]['desv_est'])} %. (3) Con {R['n']-1} datos las bandas son amplias. (4) Se necesita además la inspección de la gráfica y pruebas formales (ADF, KPSS, Phillips-Perron); la ADF aquí es solo orientativa (p = {n3(R['adf_n_p'])} en nivel y p < 0.001 en cambio logarítmico)."),
]
Q[14] = [
 ("¿Observan uno o varios movimientos que sobresalgan claramente?",
  f"Sobresale **nov-2024** (+93.59 % logarítmico; z = {ep['2024-11']['z']:.2f}), el único mes con |z| > 2. Siguen jul-2026 ({sg1(ep['2026-07']['Cambio log (%)'])} %, z = {ep['2026-07']['z']:.2f}), may-2026 ({sg1(ep['2026-05']['Cambio log (%)'])} %, z = {ep['2026-05']['z']:.2f}), nov-2025 ({sg1(ep['2025-11']['Cambio log (%)'])} %), dic-2025 ({sg1(ep['2025-12']['Cambio log (%)'])} %), sep-2023 ({sg1(ep['2023-09']['Cambio log (%)'])} %), feb-2025 ({sg1(ep['2025-02']['Cambio log (%)'])} %) y jun-2026 ({sg1(ep['2026-06']['Cambio log (%)'])} %): {R['n_z15']} de {R['n']-1} meses tienen |z| > 1.5."),
 ("¿Parece un solo punto atípico o un episodio de varios periodos?",
  f"Ambos. **nov-2024** es un punto extremo aislado, pero forma parte de un episodio mayor: {rach[0]['largo']} alzas consecutivas entre {rach[0]['inicio']} y {rach[0]['fin']} (+{n1(rach[0]['acumulado'])} % logarítmico acumulado), tras el cual el precio se instaló en un rango más alto (nunca bajó de 17.88 USD): es un **posible cambio de nivel o de régimen**. Otros episodios: abr–ago-2025 ({rach[1]['largo']} alzas, +{n1(rach[1]['acumulado'])} %) y el ciclo may–jul-2026 (máximo de 143.48 USD y luego dos caídas seguidas, −50.9 % desde el pico). La volatilidad móvil muestra regímenes: calma en {fm(R['f_vm_min'])} ({n1(R['vm_min'])} %), pico en {fm(R['f_vm_max'])} ({n1(R['vm_max'])} %) y nivel alto (26–38 %) desde nov-2025."),
 ("¿Eliminarían automáticamente esa observación? ¿Por qué?",
  f"No. Son precios reales, no errores de captura: el «% var.» de la fuente coincide con el cálculo y los cierres están dentro del rango del mes. Además, los meses extremos coinciden con volumen alto (nov-2024: 600.43 M; may-2026: 603.74 M; jun-2026: 634.08 M, frente a una mediana de {n1(R['vol_med_total'])} M; correlación entre |cambio logarítmico| y volumen = {R['corr_abs_vol']:.2f}), consistente con eventos de mercado reales. Eliminarlos ocultaría justamente el riesgo de la acción. Antes de cualquier tratamiento habría que investigar la causa (noticias, resultados, lanzamientos), algo que esta base no permite identificar."),
]
Q[15] = [
 ("1. ¿Cuáles son las principales características temporales de la serie?",
  f"RKLB tiene (a) **tendencia ascendente muy fuerte y casi exponencial** (de {n2(R['primero'])} a {n2(R['ultimo'])} USD; ≈ {n1(R['g_mensual'])} % mensual compuesto en la tendencia log-lineal), con un máximo de {n2(R['maximo'])} USD en {fm(R['f_max'])} y una corrección posterior de {abs(R['caida_max']):.0f} %; (b) **variabilidad creciente** con el nivel (desviación del precio de {n2(pa[2023]['desv_est'])} USD en 2023 a {n2(pa[2026]['desv_est'])} USD en 2026); (c) **alta persistencia en nivel** (autocorrelación de rezago 1 = 0.906); (d) **cambios mensuales muy grandes** (desviación del cambio logarítmico de {n1(R['r_std'])} %); y (e) un **cambio de régimen** hacia precios altos desde nov-2024. No se observó estacionalidad."),
 ("2. ¿Qué transformación modifica de manera más clara su comportamiento y por qué?",
  f"El **cambio logarítmico mensual** (el cambio simple se comporta casi igual, pero es asimétrico y no aditivo). Convierte una serie con tendencia en una que oscila alrededor de cero: la autocorrelación de rezago 1 cae de 0.906 a {n3(R['lag1_ret'])} y ADF (orientativa) pasa de p = {n3(R['adf_n_p'])} a p < 0.001. Además, expresa los movimientos en términos relativos, comparables entre 2023 y 2026. ln(Y) solo cambia la escala (autocorr. 0.977) y ΔY quita la tendencia pero conserva la heterocedasticidad ({n2(R['d_std_h1'])} → {n2(R['d_std_h2'])} USD)."),
 ("3. ¿Qué revelan ACF y PACF sobre la dependencia temporal?",
  f"En nivel, la ACF muestra una dependencia fuerte y persistente: {n3(A('acf_nivel',1,'ACF'))} en el rezago 1, rezagos 1–4 fuera de bandas y decaimiento lento hasta ≈ 0 en el rezago 15. La PACF revela que casi toda esa dependencia es **directa del mes anterior** ({n3(A('pacf_nivel',1,'PACF'))}); el efecto de rezagos 2–4 en la ACF es en cadena (PACF en el rezago 2 = {n3(A('pacf_nivel',2,'PACF'))}). Esto es típico de una serie que se comporta como una caminata aleatoria: el mejor predictor del precio de un mes es el del mes anterior."),
 ("4. ¿Cómo cambia esa dependencia al pasar del nivel a la serie transformada?",
  f"Desaparece casi por completo: el rezago 1 pasa de {n3(A('acf_nivel',1,'ACF'))} a {n3(A('acf_ret',1,'ACF'))}; de 4 barras de ACF y 3 de PACF fuera de bandas se pasa a ninguna; la suma de |ACF| baja de {n2(R['sum_abs_n'])} a {n2(R['sum_abs_r'])} (≈ ruido blanco) y Ljung-Box pasa de p < 0.0001 a p = {n3(R['lb_r_p'])}. La dependencia lineal que quedaba era la de la tendencia, no un comportamiento predecible en los cambios."),
 ("5. ¿Existen observaciones atípicas, episodios o posibles cambios importantes?",
  f"Sí. El mes atípico principal es **nov-2024** (+154.95 % simple; +93.59 % logarítmico; z = {ep['2024-11']['z']:.2f}); también destacan may-2026 (+73.9 %), dic-2025 (+65.5 %), nov-2025 (−33.1 %), jun-2026 (−29.2 %) y jul-2026 (−36.1 %). Hay episodios de alzas consecutivas (may–nov-2024 y abr–ago-2025), un posible **cambio de nivel** tras nov-2024 y regímenes de volatilidad (calma en jul-2024 con {n1(R['vm_min'])} % y picos de hasta {n1(R['vm_max'])} % en abr-2025). Los meses extremos coinciden con volúmenes altos, por lo que parecen eventos reales y no errores."),
 ("6. ¿Qué representación consideran más adecuada para continuar posteriormente con el modelado y por qué?",
  f"El **cambio logarítmico mensual**, 100·[ln(Yt) − ln(Yt−1)]: (i) elimina la tendencia sin perder interpretación económica (variación porcentual continua); (ii) su ACF/PACF no muestra dependencia significativa, lo que es apropiado como punto de partida; (iii) es aditivo, así que los pronósticos acumulados se convierten de vuelta a precio con la exponencial; y (iv) hace comparables 2023 y 2026. Dos advertencias para la siguiente etapa: la media mensual ({n2(R['r_media'])} %) no es distinguible de cero (t ≈ {t_media:.2f}), así que la predicción de la media será difícil; y como la volatilidad cambia ({n1(R['vm_min'])} %–{n1(R['vm_max'])} %), conviene considerar un modelo de volatilidad condicional. Debe estimarse solo con Train ({fm(R['tr_ini'])}–{fm(R['tr_fin'])}) y evaluarse en Test."),
 ("7. ¿Cuáles son las principales limitaciones de su diagnóstico?",
  f"(a) **Muestra corta**: {R['n']} meses ({R['n']-1} cambios); las bandas de confianza son anchas (±0.28 a ±0.83) y los rezagos lejanos se estiman con pocos pares. (b) **20 rezagos evaluados al 5 %**: se espera ≈ 1 barra fuera por azar. (c) El último mes ({fm(R['fin'])}) es **parcial**. (d) Se usan datos de cierre mensual: se pierde la variación dentro del mes (por ejemplo, jul-2026 abrió en 101.2 y tocó 107.6 y 58.2 USD). (e) El diagnóstico es descriptivo: ADF y Ljung-Box son orientativas, sin pruebas formales de cambio estructural, KPSS ni heterocedasticidad (ARCH). (f) No se investigaron las causas de los episodios atípicos. (g) Train y Test pertenecen a regímenes de precio muy distintos ({n2(R['media_train'])} vs {n2(R['media_test'])} USD) y Test tiene solo {R['n_test']} meses. (h) El ACF se calculó con toda la muestra con fines de diagnóstico; en el modelado debe calcularse solo con Train. (i) Los resultados describen a RKLB en este periodo y no son generalizables."),
]

PREGUNTAS_SEC = {1: "1. Identificación y carga de datos", 2: "2. Revisión, limpieza y preparación", 3: "3. Serie en nivel", 4: "4. Primera diferencia",
                 5: "5. Logaritmo natural", 6: "6. Cambio porcentual simple", 7: "7. Cambio logarítmico", 8: "8. Comparación de transformaciones",
                 9: "9. División Train/Test", 10: "10. Rezagos y autocorrelación", 11: "11. Correlograma ACF en nivel", 12: "12. Correlograma PACF en nivel",
                 13: "13. ACF y PACF de la serie transformada", 14: "14. Observaciones atípicas, episodios y posibles cambios", 15: "15. Conclusión diagnóstica integradora"}
