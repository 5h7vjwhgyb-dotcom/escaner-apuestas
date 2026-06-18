"""
verificador.py — Verificación Automática de Resultados
Evalúa picks pendientes contra resultados reales del Mundial.
Lógica directa en código para picks estándar (Over/Under, 1X2, DC).
Usa Gemini solo como fallback para picks no reconocidos.
"""

import requests
import re
import streamlit as st
from typing import Dict, List, Optional, Tuple
import json
import bd

# ═══════════════════════════════════════════════════════════════
# TRADUCCIONES (para comparar nombres de equipos)
# ═══════════════════════════════════════════════════════════════
PAISES_ES = {
    "Germany":"Alemania","France":"Francia","Spain":"España","Italy":"Italia",
    "Brazil":"Brasil","Argentina":"Argentina","England":"Inglaterra",
    "Portugal":"Portugal","Netherlands":"Países Bajos","Belgium":"Bélgica",
    "Croatia":"Croacia","Uruguay":"Uruguay","Mexico":"México",
    "United States":"EE.UU.","USA":"EE.UU.","Japan":"Japón",
    "South Korea":"Corea del Sur","Australia":"Australia","Senegal":"Senegal",
    "Morocco":"Marruecos","Tunisia":"Túnez","Cameroon":"Camerún",
    "Ghana":"Ghana","Nigeria":"Nigeria","Ivory Coast":"Costa de Marfil",
    "Egypt":"Egipto","Saudi Arabia":"Arabia Saudita","Iran":"Irán",
    "Qatar":"Catar","Switzerland":"Suiza","Poland":"Polonia",
    "Denmark":"Dinamarca","Sweden":"Suecia","Norway":"Noruega",
    "Ecuador":"Ecuador","Colombia":"Colombia","Peru":"Perú",
    "Chile":"Chile","Paraguay":"Paraguay","Bolivia":"Bolivia",
    "Venezuela":"Venezuela","Turkey":"Türkiye","Serbia":"Serbia",
    "Ukraine":"Ucrania","Austria":"Austria","Wales":"Gales","Scotland":"Escocia",
    "Canada":"Canadá","Costa Rica":"Costa Rica","Panama":"Panamá",
    "Honduras":"Honduras","Jamaica":"Jamaica","New Zealand":"Nueva Zelanda",
    "Curaçao":"Curazao","Cape Verde":"Cabo Verde","Algeria":"Argelia",
}

def tr(n): return PAISES_ES.get(n, n)

def nombres_equipo(nombre_en: str) -> List[str]:
    """Retorna todas las variantes del nombre de un equipo para matching."""
    nombre_es = tr(nombre_en)
    variantes = {
        nombre_en.lower(),
        nombre_es.lower(),
        nombre_en.lower().replace(" ", ""),
        nombre_es.lower().replace(" ", ""),
    }
    # Alias especiales
    alias = {
        "united states": ["estados unidos", "ee.uu.", "usa", "eeuu"],
        "ivory coast":   ["costa de marfil", "côte d'ivoire"],
        "south korea":   ["corea del sur", "korea"],
        "new zealand":   ["nueva zelanda", "nueva zelandia"],
        "iran":          ["irán", "iran"],
        "curacao":       ["curazao", "curaçao"],
    }
    variantes.update(alias.get(nombre_en.lower(), []))
    return list(variantes)

# ═══════════════════════════════════════════════════════════════
# LÓGICA DIRECTA DE EVALUACIÓN
# ═══════════════════════════════════════════════════════════════

def evaluar_pick(
    seleccion:  str,
    home_team:  str,
    away_team:  str,
    home_score: int,
    away_score: int,
) -> str:
    """
    Evalúa si un pick fue ACERTADO o FALLIDO basado en el resultado real.
    Retorna: "acertado" | "fallido" | "pendiente" (si no puede determinarlo)
    """
    sel   = seleccion.lower().strip()
    total = home_score + away_score
    diff  = home_score - away_score

    if   diff > 0: resultado = "home"
    elif diff < 0: resultado = "away"
    else:          resultado = "draw"

    # ── Over / Under ─────────────────────────────────────────
    patron_ou = re.search(r'(over|under|más de|menos de|mas de)\s*([\d.]+)', sel)
    if patron_ou:
        direccion = patron_ou.group(1)
        umbral    = float(patron_ou.group(2))
        if "over" in direccion or "más" in direccion or "mas" in direccion:
            return "acertado" if total > umbral else "fallido"
        else:
            return "acertado" if total < umbral else "fallido"

    # ── Ambos Marcan (BTTS) ──────────────────────────────────
    if any(k in sel for k in ["ambos marcan", "btts", "both teams"]):
        ambos = home_score > 0 and away_score > 0
        if "no" in sel or "no marcan" in sel:
            return "acertado" if not ambos else "fallido"
        return "acertado" if ambos else "fallido"

    # ── Resultado 1X2 directo ────────────────────────────────
    if sel in ("1", "local", "victoria local", "home", "gana local"):
        return "acertado" if resultado == "home" else "fallido"
    if sel in ("x", "empate", "draw", "iguales"):
        return "acertado" if resultado == "draw" else "fallido"
    if sel in ("2", "visitante", "victoria visitante", "away", "gana visitante"):
        return "acertado" if resultado == "away" else "fallido"

    # ── Doble Oportunidad (DC) ───────────────────────────────
    if sel in ("1x", "local o empate", "home or draw", "no gana visitante"):
        return "acertado" if resultado in ("home", "draw") else "fallido"
    if sel in ("x2", "empate o visitante", "draw or away", "no gana local"):
        return "acertado" if resultado in ("draw", "away") else "fallido"
    if sel in ("12", "local o visitante", "sin empate", "no empate", "home or away"):
        return "acertado" if resultado in ("home", "away") else "fallido"

    # ── DC con nombre de equipo (ej: "Irán o Empate") ────────
    nombres_home = nombres_equipo(home_team)
    nombres_away = nombres_equipo(away_team)

    menciona_home = any(n in sel for n in nombres_home)
    menciona_away = any(n in sel for n in nombres_away)
    menciona_emp  = any(k in sel for k in ["empate", "o empate", "draw", "x"])

    if menciona_home and menciona_emp and not menciona_away:
        # DC: Home o Empate (1X)
        return "acertado" if resultado in ("home", "draw") else "fallido"
    if menciona_away and menciona_emp and not menciona_home:
        # DC: Away o Empate (X2)
        return "acertado" if resultado in ("away", "draw") else "fallido"
    if menciona_home and menciona_away and not menciona_emp:
        # DC: Home o Away (12)
        return "acertado" if resultado in ("home", "away") else "fallido"
    if menciona_home and not menciona_emp and not menciona_away:
        # Ganador: Home
        return "acertado" if resultado == "home" else "fallido"
    if menciona_away and not menciona_emp and not menciona_home:
        # Ganador: Away
        return "acertado" if resultado == "away" else "fallido"

    # ── No pudo determinarse ──────────────────────────────────
    return "pendiente"

def partido_coincide(partido_str: str, home_api: str, away_api: str) -> bool:
    """
    Verifica si un string de partido (ej: "Irán vs Nueva Zelanda")
    corresponde a los equipos de la API (en inglés).
    """
    p = partido_str.lower()
    nombres_h = nombres_equipo(home_api)
    nombres_a = nombres_equipo(away_api)
    return any(n in p for n in nombres_h) and any(n in p for n in nombres_a)

# ═══════════════════════════════════════════════════════════════
# OBTENER SCORES DESDE ODDS API
# ═══════════════════════════════════════════════════════════════

def obtener_scores_completados(api_odds: str, sport: str = "soccer_fifa_world_cup") -> List[Dict]:
    """
    Obtiene partidos completados con marcadores desde Odds API.
    Retorna lista de {home_team, away_team, home_score, away_score}.
    """
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/scores/",
            params={"apiKey": api_odds, "daysFrom": 10},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[verificador] Scores API error: {r.status_code} — {r.text[:100]}")
            return []

        completados = []
        for m in r.json():
            if not m.get("completed"):
                continue
            scores = m.get("scores", [])
            if len(scores) < 2:
                continue
            home = m.get("home_team", "")
            away = m.get("away_team", "")
            s_dict = {}
            for s in scores:
                if s.get("name") and s.get("score") is not None:
                    try: s_dict[s["name"]] = int(s["score"])
                    except: pass
            if home not in s_dict or away not in s_dict:
                continue
            completados.append({
                "home_team":  home,
                "away_team":  away,
                "home_score": s_dict[home],
                "away_score": s_dict[away],
                "match_str":  f"{tr(home)} vs {tr(away)}",
            })
        return completados
    except Exception as e:
        print(f"[verificador] Error obtener_scores: {e}")
        return []

def diagnostico_scores(api_odds: str) -> Dict:
    """
    Retorna diagnóstico de qué scores están disponibles.
    Útil para debugging desde la UI.
    """
    scores = obtener_scores_completados(api_odds)
    pendientes_hist = 0
    try:
        p = bd.get_client().table("historial").select("id").or_(
            "res_estrella.eq.pendiente,res_mas_seguro.eq.pendiente,"
            "res_segura.eq.pendiente,res_moderada.eq.pendiente,res_arriesgada.eq.pendiente"
        ).execute().data
        pendientes_hist = len(p)
    except: pass

    return {
        "scores_disponibles": len(scores),
        "partidos": [f"{s['match_str']} ({s['home_score']}-{s['away_score']})" for s in scores],
        "picks_pendientes_historial": pendientes_hist,
    }

# ═══════════════════════════════════════════════════════════════
# VERIFICACIÓN DE HISTORIAL (tabla historial)
# ═══════════════════════════════════════════════════════════════

def verificar_historial(api_odds: str) -> Tuple[int, int]:
    """
    Verifica y actualiza picks pendientes en la tabla historial.
    Retorna (actualizados, pendientes_restantes).
    """
    try:
        # Obtener tickets con picks pendientes
        pendientes = bd.get_client().table("historial").select("*").or_(
            "res_estrella.eq.pendiente,"
            "res_mas_seguro.eq.pendiente,"
            "res_segura.eq.pendiente,"
            "res_moderada.eq.pendiente,"
            "res_arriesgada.eq.pendiente"
        ).execute().data

        if not pendientes:
            return 0, 0

        # Obtener scores completados
        scores = obtener_scores_completados(api_odds)
        if not scores:
            return 0, len(pendientes)

        actualizados = 0

        for ticket in pendientes:
            analisis = json.loads(ticket.get("analisis_json", "{}"))
            partidos_str = ticket.get("partidos", "")

            # Definir qué pick va en cada columna
            estrategias = analisis.get("estrategias", [])
            columnas = {
                "res_estrella":   {
                    "seleccion": analisis.get("pick_estrella", {}).get("seleccion", ""),
                    "partido":   analisis.get("pick_estrella", {}).get("partido", partidos_str),
                },
                "res_mas_seguro": {
                    "seleccion": analisis.get("pick_mas_seguro", {}).get("seleccion", ""),
                    "partido":   analisis.get("pick_mas_seguro", {}).get("partido", partidos_str),
                },
                "res_segura":    {
                    "seleccion": " | ".join(estrategias[0].get("picks", [])) if len(estrategias) > 0 else "",
                    "partido":   partidos_str,
                },
                "res_moderada":  {
                    "seleccion": " | ".join(estrategias[1].get("picks", [])) if len(estrategias) > 1 else "",
                    "partido":   partidos_str,
                },
                "res_arriesgada":{
                    "seleccion": " | ".join(estrategias[2].get("picks", [])) if len(estrategias) > 2 else "",
                    "partido":   partidos_str,
                },
            }

            updates = {}
            for col, info in columnas.items():
                if ticket.get(col) != "pendiente":
                    continue
                sel     = info["seleccion"]
                partido = info["partido"]
                if not sel:
                    continue

                # Buscar el score del partido correspondiente
                for score in scores:
                    if partido_coincide(partido, score["home_team"], score["away_team"]):
                        resultado = evaluar_pick(
                            sel,
                            score["home_team"],
                            score["away_team"],
                            score["home_score"],
                            score["away_score"],
                        )
                        if resultado in ("acertado", "fallido"):
                            updates[col] = resultado
                        break

            if updates:
                bd.get_client().table("historial").update(updates).eq("id", ticket["id"]).execute()
                actualizados += len(updates)

        restantes = len(pendientes) - (1 if actualizados > 0 else 0)
        return actualizados, max(restantes, 0)

    except Exception as e:
        print(f"[verificador] Error verificar_historial: {e}")
        return 0, 0

# ═══════════════════════════════════════════════════════════════
# VERIFICACIÓN DE PICKS +EV (tabla valor_detectado)
# ═══════════════════════════════════════════════════════════════

def verificar_valor_detectado(api_odds: str, competition: str = "FIFA World Cup") -> Tuple[int, int]:
    """
    Verifica y actualiza picks pendientes en la tabla valor_detectado.
    Retorna (actualizados, pendientes_restantes).
    """
    try:
        pendientes = bd.get_valores_pendientes(competition)
        if not pendientes:
            return 0, 0

        sport_key = "soccer_fifa_world_cup" if "World Cup" in competition else "soccer_epl"
        scores    = obtener_scores_completados(api_odds, sport_key)
        if not scores:
            return 0, len(pendientes)

        actualizados = 0
        for pick in pendientes:
            home = pick.get("home_team", "")
            away = pick.get("away_team", "")
            sel  = pick.get("seleccion", "")

            for score in scores:
                if partido_coincide(f"{home} vs {away}", score["home_team"], score["away_team"]):
                    resultado = evaluar_pick(
                        sel,
                        score["home_team"],
                        score["away_team"],
                        score["home_score"],
                        score["away_score"],
                    )
                    if resultado in ("acertado", "fallido"):
                        bd.actualizar_resultado_valor(pick["id"], resultado)
                        actualizados += 1
                    break

        return actualizados, len(pendientes) - actualizados

    except Exception as e:
        print(f"[verificador] Error verificar_valor_detectado: {e}")
        return 0, 0

# ═══════════════════════════════════════════════════════════════
# VERIFICACIÓN COMPLETA (historial + valor_detectado)
# ═══════════════════════════════════════════════════════════════

def verificar_todo(api_odds: str) -> Dict:
    """
    Ejecuta verificación completa de todos los picks pendientes.
    Retorna resumen de lo que se actualizó.
    """
    act_hist, pend_hist   = verificar_historial(api_odds)
    act_ev,   pend_ev     = verificar_valor_detectado(api_odds)

    return {
        "historial_actualizados": act_hist,
        "historial_pendientes":   pend_hist,
        "ev_actualizados":        act_ev,
        "ev_pendientes":          pend_ev,
        "total_actualizados":     act_hist + act_ev,
    }
