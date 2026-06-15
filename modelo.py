"""
modelo.py — Motor de Predicción Dixon-Coles
Genera probabilidades propias para cada partido y detecta valor (+EV).
No consume llamadas a la API — trabaja 100% con datos de Supabase.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from typing import Dict, List, Optional, Tuple
import streamlit as st
import bd

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL MODELO
# ═══════════════════════════════════════════════════════════════

MIN_PARTIDOS = 5     # Mínimo de partidos finalizados para entrenar
MAX_GOLES    = 8     # Máximo de goles a modelar en la distribución
MIN_EV       = 0.04  # Edge mínimo para considerar una apuesta (+4%)

# ═══════════════════════════════════════════════════════════════
# NÚCLEO MATEMÁTICO — DIXON-COLES
# ═══════════════════════════════════════════════════════════════

def tau(x: int, y: int, lh: float, la: float, rho: float) -> float:
    """
    Factor de corrección Dixon-Coles para marcadores bajos (0-0, 1-0, 0-1, 1-1).
    Corrige la sobreestimación de Poisson en resultados de pocos goles.
    """
    if x == 0 and y == 0: return 1.0 - lh * la * rho
    if x == 0 and y == 1: return 1.0 + lh * rho
    if x == 1 and y == 0: return 1.0 + la * rho
    if x == 1 and y == 1: return 1.0 - rho
    return 1.0

def neg_log_likelihood(
    params:   np.ndarray,
    partidos: List[Dict],
    equipos:  List[str],
) -> float:
    """
    Verosimilitud negativa del modelo Dixon-Coles.
    Se minimiza para encontrar los parámetros óptimos.
    Parámetros: [ataque_0..n, defensa_0..n, home_adv, rho]
    """
    n   = len(equipos)
    idx = {t: i for i, t in enumerate(equipos)}

    ataque   = params[:n]
    defensa  = params[n:2 * n]
    home_adv = params[2 * n]
    rho      = params[2 * n + 1]

    log_lik = 0.0
    for p in partidos:
        i = idx.get(p["home_team"])
        j = idx.get(p["away_team"])
        if i is None or j is None:
            continue

        hg = int(p["home_goals"])
        ag = int(p["away_goals"])
        w  = float(p.get("weight", 1.0))

        # Goles esperados (lambda)
        lh = np.exp(ataque[i] - defensa[j] + home_adv)
        la = np.exp(ataque[j] - defensa[i])

        # Probabilidades de Poisson
        p_hg = poisson.pmf(hg, lh)
        p_ag = poisson.pmf(ag, la)

        # Corrección Dixon-Coles
        t = tau(hg, ag, lh, la, rho)

        if t <= 0 or p_hg < 1e-10 or p_ag < 1e-10:
            continue

        log_lik += w * (np.log(max(t, 1e-10)) + np.log(p_hg) + np.log(p_ag))

    return -log_lik

def ajustar_modelo(partidos: List[Dict]) -> Optional[Dict]:
    """
    Ajusta los parámetros Dixon-Coles por máxima verosimilitud.
    Retorna diccionario con todos los parámetros del modelo o None si falla.
    """
    if len(partidos) < MIN_PARTIDOS:
        return None

    equipos = sorted(set(
        [p["home_team"] for p in partidos] +
        [p["away_team"] for p in partidos]
    ))
    n = len(equipos)
    if n < 2:
        return None

    # Parámetros iniciales
    params_0 = np.zeros(2 * n + 2)
    params_0[2 * n]     = 0.25   # Home advantage
    params_0[2 * n + 1] = 0.05   # Rho (corrección)

    # Límites por parámetro
    bounds = (
        [(-2.5, 2.5)] * n +   # Ataque
        [(-2.5, 2.5)] * n +   # Defensa
        [(0.0,  1.5)]      +   # Home advantage
        [(-0.4, 0.4)]          # Rho
    )

    # Restricción: suma de ataques = 0 (identificabilidad del modelo)
    constraints = [{"type": "eq", "fun": lambda p: np.sum(p[:n])}]

    try:
        res = minimize(
            neg_log_likelihood,
            params_0,
            args=(partidos, equipos),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 2000, "ftol": 1e-9},
        )

        # Si SLSQP no converge, intentar L-BFGS-B sin restricción
        if not res.success:
            res = minimize(
                neg_log_likelihood,
                params_0,
                args=(partidos, equipos),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 2000},
            )

        p = res.x
        return {
            "equipos":    equipos,
            "ataque":     dict(zip(equipos, p[:n])),
            "defensa":    dict(zip(equipos, p[n:2 * n])),
            "home_adv":   float(p[2 * n]),
            "rho":        float(p[2 * n + 1]),
            "n_partidos": len(partidos),
            "convergido": bool(res.success),
            "log_lik":    float(-res.fun),
        }
    except Exception as e:
        print(f"[modelo] Error ajustar_modelo: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE MARCADORES
# ═══════════════════════════════════════════════════════════════

def distribucion_marcadores(lh: float, la: float, rho: float) -> np.ndarray:
    """
    Genera la matriz de probabilidades de todos los marcadores posibles.
    M[i][j] = P(local marca i goles, visitante marca j goles).
    """
    M = np.zeros((MAX_GOLES + 1, MAX_GOLES + 1))
    for i in range(MAX_GOLES + 1):
        for j in range(MAX_GOLES + 1):
            t       = tau(i, j, lh, la, rho)
            M[i][j] = max(t, 0.0) * poisson.pmf(i, lh) * poisson.pmf(j, la)

    # Normalizar
    total = M.sum()
    if total > 0:
        M /= total
    return M

def marcador_mas_probable(M: np.ndarray) -> str:
    """Retorna el marcador más probable y su probabilidad."""
    idx  = np.unravel_index(np.argmax(M), M.shape)
    prob = M[idx]
    return f"{idx[0]}-{idx[1]} ({prob * 100:.1f}%)"

# ═══════════════════════════════════════════════════════════════
# PREDICCIÓN DE PARTIDO
# ═══════════════════════════════════════════════════════════════

def predecir_partido(home: str, away: str, params: Dict) -> Optional[Dict]:
    """
    Genera predicción completa para un partido usando los parámetros del modelo.
    Retorna probabilidades 1X2, Over/Under, Ambos Marcan y marcador más probable.
    Si un equipo es nuevo (no está en params), usa valor neutro.
    """
    try:
        # Parámetros del equipo (valor neutro 0.0 si es equipo nuevo)
        at_h = params["ataque"].get(home, 0.0)
        df_a = params["defensa"].get(away, 0.0)
        at_a = params["ataque"].get(away, 0.0)
        df_h = params["defensa"].get(home, 0.0)
        rho  = params["rho"]

        # Goles esperados
        lh = np.exp(at_h - df_a + params["home_adv"])
        la = np.exp(at_a - df_h)

        # Distribución de marcadores
        M = distribucion_marcadores(lh, la, rho)

        # Probabilidades 1X2
        prob_home = float(np.tril(M, -1).sum())   # Local gana
        prob_draw = float(np.diag(M).sum())        # Empate
        prob_away = float(np.triu(M, 1).sum())     # Visitante gana

        # Over/Under usando máscara numpy
        goles_totales = np.array(
            [[i + j for j in range(MAX_GOLES + 1)] for i in range(MAX_GOLES + 1)]
        )
        prob_over25  = float(M[goles_totales > 2].sum())
        prob_under25 = float(M[goles_totales <= 2].sum())
        prob_over15  = float(M[goles_totales > 1].sum())
        prob_under15 = float(M[goles_totales <= 1].sum())

        # Ambos equipos marcan (BTTS)
        prob_btts_si = float(M[1:, 1:].sum())
        prob_btts_no = float(M[:1, :].sum() + M[1:, :1].sum())

        # Doble oportunidad
        prob_1x = prob_home + prob_draw
        prob_x2 = prob_draw + prob_away
        prob_12 = prob_home + prob_away

        return {
            "home_team":    home,
            "away_team":    away,
            "lambda_home":  round(float(lh), 3),
            "lambda_away":  round(float(la), 3),
            # 1X2
            "prob_home":    round(prob_home, 4),
            "prob_draw":    round(prob_draw, 4),
            "prob_away":    round(prob_away, 4),
            # Doble oportunidad
            "prob_1x":      round(prob_1x, 4),
            "prob_x2":      round(prob_x2, 4),
            "prob_12":      round(prob_12, 4),
            # Over/Under
            "prob_over15":  round(prob_over15, 4),
            "prob_under15": round(prob_under15, 4),
            "prob_over25":  round(prob_over25, 4),
            "prob_under25": round(prob_under25, 4),
            # BTTS
            "prob_btts_si": round(prob_btts_si, 4),
            "prob_btts_no": round(prob_btts_no, 4),
            # Extra
            "marcador_probable": marcador_mas_probable(M),
            "equipo_nuevo_home": home not in params["ataque"],
            "equipo_nuevo_away": away not in params["ataque"],
        }
    except Exception as e:
        print(f"[modelo] Error predecir_partido {home} vs {away}: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# DETECCIÓN DE VALOR (+EV)
# ═══════════════════════════════════════════════════════════════

def detectar_valor(
    prediccion:   Dict,
    cuotas:       Dict,
    min_ev:       float = MIN_EV,
) -> List[Dict]:
    """
    Compara probabilidades del modelo vs mercado.
    Detecta apuestas con valor esperado positivo (+EV).

    cuotas esperado: {
        "home": 1.80, "draw": 3.50, "away": 4.20,
        "over25": 1.90, "under25": 1.95,
        "over15": 1.35, "under15": 2.80,
        "btts_si": 1.75, "btts_no": 2.05,
        "dc_1x": 1.15, "dc_x2": 1.25, "dc_12": 1.40,
    }

    Retorna lista de picks con +EV ordenados por valor descendente.
    """
    picks = []

    # Mapa: (mercado, selección, clave_prob, clave_cuota)
    mercados = [
        ("1X2",            "Local",      "prob_home",    "home"),
        ("1X2",            "Empate",     "prob_draw",    "draw"),
        ("1X2",            "Visitante",  "prob_away",    "away"),
        ("Doble Oport.",   "1X",         "prob_1x",      "dc_1x"),
        ("Doble Oport.",   "X2",         "prob_x2",      "dc_x2"),
        ("Doble Oport.",   "12",         "prob_12",      "dc_12"),
        ("Over/Under",     "Over 2.5",   "prob_over25",  "over25"),
        ("Over/Under",     "Under 2.5",  "prob_under25", "under25"),
        ("Over/Under",     "Over 1.5",   "prob_over15",  "over15"),
        ("Over/Under",     "Under 1.5",  "prob_under15", "under15"),
        ("Ambos Marcan",   "Sí",         "prob_btts_si", "btts_si"),
        ("Ambos Marcan",   "No",         "prob_btts_no", "btts_no"),
    ]

    for mercado, seleccion, prob_key, cuota_key in mercados:
        cuota = cuotas.get(cuota_key)
        if not cuota or cuota <= 1.0:
            continue

        prob_modelo  = prediccion.get(prob_key, 0.0)
        prob_mercado = 1.0 / cuota
        ev           = (prob_modelo * cuota) - 1.0
        edge         = prob_modelo - prob_mercado

        if ev >= min_ev and edge > 0:
            kelly = kelly_fraccionado(prob_modelo, cuota)
            picks.append({
                "mercado":        mercado,
                "seleccion":      seleccion,
                "prob_modelo":    round(prob_modelo * 100, 1),   # En %
                "prob_mercado":   round(prob_mercado * 100, 1),  # En %
                "cuota":          cuota,
                "valor_esperado": round(ev * 100, 2),            # En %
                "edge":           round(edge * 100, 2),          # En %
                "kelly_pct":      kelly,                          # % del bankroll
            })

    return sorted(picks, key=lambda x: x["valor_esperado"], reverse=True)

def kelly_fraccionado(prob: float, cuota: float, fraccion: float = 0.25) -> float:
    """
    Kelly Criterion fraccionado (Kelly/4 por defecto).
    Más conservador y seguro que Kelly completo.
    Retorna % del bankroll a apostar.
    """
    b = cuota - 1.0
    q = 1.0 - prob
    k = (b * prob - q) / b if b > 0 else 0.0
    return round(max(k * fraccion * 100, 0.0), 2)

# ═══════════════════════════════════════════════════════════════
# PIPELINE COMPLETO
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def entrenar_modelo(competition: str, season: str) -> Optional[Dict]:
    """
    Carga datos históricos de Supabase y entrena el modelo.
    Cacheado 1 hora — no recalcula en cada interacción.
    SIN llamadas a la API.
    """
    from datos import get_partidos_para_modelo
    partidos = get_partidos_para_modelo(competition, season)
    if len(partidos) < MIN_PARTIDOS:
        return None
    return ajustar_modelo(partidos)

def generar_predicciones_y_valor(
    competition:    str,
    season:         str,
    cuotas_mercado: Dict = None,
) -> List[Dict]:
    """
    Pipeline completo:
    1. Entrena modelo con histórico de Supabase.
    2. Genera predicciones para próximos partidos.
    3. Detecta picks con +EV si se proveen cuotas.
    4. Guarda todo en Supabase.
    SIN llamadas a Football-Data API.
    """
    from datos import get_proximos_para_predecir

    params = entrenar_modelo(competition, season)
    if not params:
        return []

    proximos   = get_proximos_para_predecir(competition)
    resultados = []

    for partido in proximos:
        home = partido["home_team"]
        away = partido["away_team"]

        pred = predecir_partido(home, away, params)
        if not pred:
            continue

        # Guardar predicción en BD
        guardado = bd.guardar_prediccion({
            "partido_id":     partido["id"],
            "home_team":      home,
            "away_team":      away,
            "competition":    competition,
            "fecha":          partido["fecha"],
            "prob_home":      pred["prob_home"],
            "prob_draw":      pred["prob_draw"],
            "prob_away":      pred["prob_away"],
            "lambda_home":    pred["lambda_home"],
            "lambda_away":    pred["lambda_away"],
            "partidos_usados":params["n_partidos"],
        })

        # Detectar valor si hay cuotas del mercado
        picks_valor = []
        mid = partido.get("api_match_id", "")
        if cuotas_mercado and mid in cuotas_mercado and guardado:
            picks_valor = detectar_valor(pred, cuotas_mercado[mid])
            if picks_valor:
                bd.guardar_valores_bulk([{
                    "partido_id":    partido["id"],
                    "prediccion_id": guardado["id"],
                    "home_team":     home,
                    "away_team":     away,
                    "competition":   competition,
                    "fecha":         partido["fecha"],
                    "mercado":       pk["mercado"],
                    "seleccion":     pk["seleccion"],
                    "prob_modelo":   pk["prob_modelo"] / 100,
                    "prob_mercado":  pk["prob_mercado"] / 100,
                    "cuota":         pk["cuota"],
                    "valor_esperado":pk["valor_esperado"] / 100,
                    "edge":          pk["edge"],
                } for pk in picks_valor])

        resultados.append({
            "partido":    partido,
            "prediccion": pred,
            "picks":      picks_valor,
        })

    return resultados

def ranking_equipos(competition: str, season: str) -> List[Dict]:
    """
    Ranking de equipos según parámetros del modelo.
    Rating = ataque - defensa (mayor = mejor equipo).
    """
    params = entrenar_modelo(competition, season)
    if not params:
        return []

    ranking = []
    for equipo in params["equipos"]:
        at = params["ataque"].get(equipo, 0.0)
        df = params["defensa"].get(equipo, 0.0)
        ranking.append({
            "equipo":  equipo,
            "ataque":  round(at, 3),
            "defensa": round(df, 3),
            "rating":  round(at - df, 3),
        })

    return sorted(ranking, key=lambda x: x["rating"], reverse=True)

def estado_modelo(competition: str, season: str) -> Dict:
    """
    Retorna el estado actual del modelo para mostrar en dashboard.
    """
    from datos import get_estado_sincronizacion
    estado_bd = get_estado_sincronizacion(competition, season)
    params    = entrenar_modelo(competition, season)

    return {
        "competition":        competition,
        "season":             season,
        "partidos_en_bd":     estado_bd["total"],
        "partidos_finalizados":estado_bd["finalizados"],
        "partidos_pendientes":estado_bd["pendientes"],
        "modelo_entrenado":   params is not None,
        "modelo_convergido":  params.get("convergido", False) if params else False,
        "n_equipos":          len(params["equipos"]) if params else 0,
        "n_partidos_usados":  params.get("n_partidos", 0) if params else 0,
        "home_advantage":     round(params.get("home_adv", 0), 3) if params else 0,
        "listo":              params is not None and estado_bd["finalizados"] >= MIN_PARTIDOS,
    }
