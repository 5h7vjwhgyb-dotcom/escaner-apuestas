"""
elo.py — Sistema de Predicción Elo para el Mundial 2026
No requiere API de datos históricos de pago.
Calcula probabilidades W/D/L, Over/Under y BTTS usando ratings Elo.
Se actualiza automáticamente con cada resultado del torneo.
"""

import math
from scipy.stats import poisson
from typing import Dict, List, Optional, Tuple
import streamlit as st
import bd

# ═══════════════════════════════════════════════════════════════
# RATINGS ELO PRE-MUNDIAL 2026
# Fuente: eloratings.net (estimados a junio 2026)
# ═══════════════════════════════════════════════════════════════
ELO_BASE: Dict[str, float] = {
    # Candidatos al título
    "Argentina":       2140,
    "France":          2005,
    "Brazil":          1995,
    "Spain":           1988,
    "England":         1982,
    "Portugal":        1975,
    "Germany":         1958,
    "Netherlands":     1950,
    # Segunda línea
    "Belgium":         1928,
    "Croatia":         1922,
    "Italy":           1918,
    "Uruguay":         1912,
    "Morocco":         1898,
    "Colombia":        1880,
    "Japan":           1878,
    "Denmark":         1875,
    "Switzerland":     1872,
    "Serbia":          1868,
    "Austria":         1858,
    "Turkey":          1848,
    "Ukraine":         1842,
    "Poland":          1848,
    "Sweden":          1825,
    "Norway":          1818,
    "Romania":         1820,
    # CONCACAF
    "United States":   1872,
    "Mexico":          1862,
    "Canada":          1830,
    "Panama":          1742,
    "Costa Rica":      1732,
    "Honduras":        1722,
    "Jamaica":         1705,
    "El Salvador":     1685,
    # CONMEBOL (resto)
    "Ecuador":         1832,
    "Chile":           1810,
    "Peru":            1805,
    "Paraguay":        1795,
    "Venezuela":       1782,
    "Bolivia":         1715,
    # Asia
    "South Korea":     1818,
    "Australia":       1812,
    "Saudi Arabia":    1758,
    "Iran":            1752,
    "Qatar":           1742,
    "Iraq":            1755,
    "Uzbekistan":      1762,
    # África
    "Senegal":         1852,
    "Ivory Coast":     1842,
    "Nigeria":         1825,
    "Egypt":           1805,
    "Algeria":         1762,
    "Cameroon":        1778,
    "Ghana":           1772,
    "Tunisia":         1782,
    "Mali":            1762,
    "South Africa":    1742,
    "Zambia":          1732,
    "Morocco":         1898,
    # Oceania y otros
    "New Zealand":     1708,
    "Curaçao":         1682,
    "Cape Verde":      1692,
}

ELO_DEFAULT = 1750   # Rating para equipos no en la lista
K_FACTOR    = 40     # Factor K para el Mundial (más alto = más sensible a resultados)
GOLES_PROM  = 2.55   # Promedio de goles en Mundiales (últimas 3 ediciones)

# ═══════════════════════════════════════════════════════════════
# CÁLCULO DE PROBABILIDADES
# ═══════════════════════════════════════════════════════════════

def prob_victoria(elo_a: float, elo_b: float, neutral: bool = True) -> float:
    """
    Probabilidad de victoria del equipo A contra B.
    Fórmula Elo estándar. neutral=True para sedes neutrales (Mundial).
    """
    home_adv = 0 if neutral else 65
    dr       = (elo_a + home_adv) - elo_b
    return 1 / (1 + 10 ** (-dr / 400))

def calcular_probabilidades(
    home: str,
    away: str,
    ratings: Dict = None,
    neutral: bool = True,
) -> Dict:
    """
    Genera predicción completa W/D/L + Over/Under + BTTS usando Elo.
    No requiere datos históricos — funciona desde el día 1 del torneo.
    """
    elo_h = float((ratings or {}).get(home, ELO_BASE.get(home, ELO_DEFAULT)))
    elo_a = float((ratings or {}).get(away, ELO_BASE.get(away, ELO_DEFAULT)))

    # Probabilidad de victoria base (Elo)
    we = prob_victoria(elo_h, elo_a, neutral)

    # Estimar tasa de empate según competitividad del partido
    competitividad = 1 - abs(we - 0.5) * 2   # 0=desequilibrado, 1=50/50
    p_draw = 0.20 + 0.12 * competitividad     # Rango: 20%-32%

    # Distribuir probabilidades restantes proporcionalmente
    restante  = 1.0 - p_draw
    p_home    = we * restante
    p_away    = (1 - we) * restante

    # Goles esperados (calibrado con media de Mundiales)
    fuerza_rel  = elo_h / (elo_h + elo_a)
    lambda_home = GOLES_PROM * fuerza_rel * 1.05
    lambda_away = GOLES_PROM * (1 - fuerza_rel) * 0.95

    # Distribución de marcadores con Poisson
    MAX_G = 7
    M     = [[poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
              for j in range(MAX_G + 1)] for i in range(MAX_G + 1)]

    total = sum(M[i][j] for i in range(MAX_G+1) for j in range(MAX_G+1))
    if total > 0:
        M = [[M[i][j]/total for j in range(MAX_G+1)] for i in range(MAX_G+1)]

    # Over/Under
    p_over25  = sum(M[i][j] for i in range(MAX_G+1) for j in range(MAX_G+1) if i+j > 2)
    p_under25 = 1 - p_over25
    p_over15  = sum(M[i][j] for i in range(MAX_G+1) for j in range(MAX_G+1) if i+j > 1)
    p_under15 = 1 - p_over15

    # BTTS
    p_btts_si = sum(M[i][j] for i in range(1,MAX_G+1) for j in range(1,MAX_G+1))
    p_btts_no = 1 - p_btts_si

    # Doble oportunidad
    p_1x = p_home + p_draw
    p_x2 = p_draw + p_away
    p_12 = p_home + p_away

    # Marcador más probable
    max_prob = 0; marcador = "1-0"
    for i in range(MAX_G+1):
        for j in range(MAX_G+1):
            if M[i][j] > max_prob:
                max_prob = M[i][j]; marcador = f"{i}-{j}"

    return {
        "home_team":     home,
        "away_team":     away,
        "elo_home":      round(elo_h),
        "elo_away":      round(elo_a),
        "lambda_home":   round(lambda_home, 2),
        "lambda_away":   round(lambda_away, 2),
        "prob_home":     round(p_home,    4),
        "prob_draw":     round(p_draw,    4),
        "prob_away":     round(p_away,    4),
        "prob_1x":       round(p_1x,      4),
        "prob_x2":       round(p_x2,      4),
        "prob_12":       round(p_12,      4),
        "prob_over15":   round(p_over15,  4),
        "prob_under15":  round(p_under15, 4),
        "prob_over25":   round(p_over25,  4),
        "prob_under25":  round(p_under25, 4),
        "prob_btts_si":  round(p_btts_si, 4),
        "prob_btts_no":  round(p_btts_no, 4),
        "marcador_probable": f"{marcador} ({max_prob*100:.1f}%)",
        "fuente":        "elo",
    }

# ═══════════════════════════════════════════════════════════════
# ACTUALIZACIÓN ELO
# ═══════════════════════════════════════════════════════════════

def actualizar_elo_partido(
    elo_home:   float,
    elo_away:   float,
    goles_home: int,
    goles_away: int,
    neutral:    bool = True,
) -> Tuple[float, float]:
    """
    Actualiza ratings Elo después de un partido.
    Retorna (nuevo_elo_home, nuevo_elo_away).
    """
    we   = prob_victoria(elo_home, elo_away, neutral)
    wa   = 1 - we

    # Resultado real: 1 = victoria, 0.5 = empate, 0 = derrota
    if   goles_home > goles_away: s_h, s_a = 1.0, 0.0
    elif goles_home < goles_away: s_h, s_a = 0.0, 1.0
    else:                         s_h, s_a = 0.5, 0.5

    # Margen de victoria (goleadas actualizan más el Elo)
    diferencia   = abs(goles_home - goles_away)
    mult_margen  = math.log(diferencia + 1) + 1 if diferencia > 0 else 1.0
    k_efectivo   = min(K_FACTOR * mult_margen, K_FACTOR * 2)

    nuevo_h = elo_home + k_efectivo * (s_h - we)
    nuevo_a = elo_away + k_efectivo * (s_a - wa)

    return round(nuevo_h, 1), round(nuevo_a, 1)

# ═══════════════════════════════════════════════════════════════
# PERSISTENCIA EN SUPABASE
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def cargar_ratings() -> Dict:
    """
    Carga Elo actualizados desde Supabase.
    Si no hay datos, usa ratings iniciales hardcodeados.
    """
    try:
        equipos = bd.get_equipos("ELO_MUNDIAL", "2026")
        if equipos:
            return {e["team_name"]: e["ataque"] for e in equipos}
    except: pass
    return ELO_BASE.copy()

def guardar_ratings(ratings: Dict) -> bool:
    """Persiste los ratings Elo actualizados en Supabase."""
    try:
        equipos = [{
            "competition":     "ELO_MUNDIAL",
            "season":          "2026",
            "team_name":       team,
            "ataque":          float(elo),
            "defensa":         0.0,
            "partidos_jugados":0,
        } for team, elo in ratings.items()]
        bd.upsert_equipos_bulk(equipos)
        cargar_ratings.clear()
        return True
    except:
        return False

def actualizar_desde_scores(scores: List[Dict]) -> Dict:
    """
    Actualiza los ratings Elo procesando una lista de resultados.
    scores: [{"home_team":"X","away_team":"Y","home_goals":2,"away_goals":1}, ...]
    Retorna el dict de ratings actualizado.
    """
    ratings = cargar_ratings()
    actualizados = 0

    for s in scores:
        home = s.get("home_team","")
        away = s.get("away_team","")
        hg   = s.get("home_goals")
        ag   = s.get("away_goals")
        if not home or not away or hg is None or ag is None:
            continue

        elo_h = ratings.get(home, ELO_BASE.get(home, ELO_DEFAULT))
        elo_a = ratings.get(away, ELO_BASE.get(away, ELO_DEFAULT))

        nuevo_h, nuevo_a = actualizar_elo_partido(elo_h, elo_a, int(hg), int(ag))
        ratings[home] = nuevo_h
        ratings[away] = nuevo_a
        actualizados  += 1

    if actualizados > 0:
        guardar_ratings(ratings)

    return ratings

# ═══════════════════════════════════════════════════════════════
# DETECCIÓN DE VALOR (+EV)
# ═══════════════════════════════════════════════════════════════

MIN_EV  = 0.04   # Edge mínimo +4%

def detectar_valor_elo(
    home:   str,
    away:   str,
    cuotas: Dict,
    ratings: Dict = None,
) -> List[Dict]:
    """
    Compara probabilidades Elo vs cuotas del mercado.
    Retorna picks con valor esperado positivo (+EV).
    """
    pred = calcular_probabilidades(home, away, ratings)
    picks = []

    mercados = [
        ("1X2",           "Local",     "prob_home",    cuotas.get("home")),
        ("1X2",           "Empate",    "prob_draw",    cuotas.get("draw")),
        ("1X2",           "Visitante", "prob_away",    cuotas.get("away")),
        ("Doble Oport.",  "1X",        "prob_1x",      cuotas.get("dc_1x")),
        ("Doble Oport.",  "X2",        "prob_x2",      cuotas.get("dc_x2")),
        ("Doble Oport.",  "12",        "prob_12",      cuotas.get("dc_12")),
        ("Over/Under",    "Over 2.5",  "prob_over25",  cuotas.get("over25")),
        ("Over/Under",    "Under 2.5", "prob_under25", cuotas.get("under25")),
        ("Over/Under",    "Over 1.5",  "prob_over15",  cuotas.get("over15")),
        ("Ambos Marcan",  "Sí",        "prob_btts_si", cuotas.get("btts_si")),
        ("Ambos Marcan",  "No",        "prob_btts_no", cuotas.get("btts_no")),
    ]

    for mercado, seleccion, prob_key, cuota in mercados:
        if not cuota or cuota <= 1.0:
            continue
        prob_modelo  = pred.get(prob_key, 0.0)
        prob_mercado = 1.0 / cuota
        ev           = (prob_modelo * cuota) - 1.0
        edge         = prob_modelo - prob_mercado

        if ev >= MIN_EV and edge > 0:
            b     = cuota - 1.0
            kelly = max(((b * prob_modelo - (1-prob_modelo)) / b) * 0.25 * 100, 0)
            picks.append({
                "mercado":        mercado,
                "seleccion":      seleccion,
                "prob_modelo":    round(prob_modelo * 100, 1),
                "prob_mercado":   round(prob_mercado * 100, 1),
                "cuota":          cuota,
                "valor_esperado": round(ev * 100, 2),
                "edge":           round(edge * 100, 2),
                "kelly_pct":      round(kelly, 2),
            })

    return sorted(picks, key=lambda x: x["valor_esperado"], reverse=True)

# ═══════════════════════════════════════════════════════════════
# RANKING ELO
# ═══════════════════════════════════════════════════════════════

def ranking_elo(ratings: Dict = None) -> List[Dict]:
    """Ranking de equipos por rating Elo actual."""
    r = ratings or cargar_ratings()
    return sorted(
        [{"equipo": team, "elo": round(elo)} for team, elo in r.items()],
        key=lambda x: x["elo"],
        reverse=True,
    )
