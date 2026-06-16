"""
datos.py — Recolección de Datos (API-Sports · api-football.com)
Reemplaza Football-Data.org. Optimizado para 100 llamadas diarias.
Dashboard: dashboard.api-football.com
"""

import requests
import streamlit as st
from datetime import datetime, date
from typing import Optional, List, Dict
import bd

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

BASE_URL = "https://v3.football.api-sports.io"

# IDs de liga en API-Sports
COMPETICIONES = {
    "FIFA World Cup":  1,
    "Premier League":  39,
    "La Liga":         140,
    "Serie A":         135,
    "Bundesliga":      78,
    "Ligue 1":         61,
}

TEMPORADA_MUNDIAL = "2026"
TEMPORADA_LIGAS   = "2024"

# Status de API-Sports → nuestro formato interno
STATUS_MAP = {
    "NS":   "scheduled",
    "TBD":  "scheduled",
    "1H":   "in_play",
    "HT":   "in_play",
    "2H":   "in_play",
    "ET":   "in_play",
    "BT":   "in_play",
    "P":    "in_play",
    "INT":  "in_play",
    "LIVE": "in_play",
    "FT":   "finished",
    "AET":  "finished",
    "PEN":  "finished",
    "PST":  "postponed",
    "CANC": "postponed",
    "ABD":  "postponed",
    "AWD":  "finished",
    "WO":   "finished",
}

# ═══════════════════════════════════════════════════════════════
# CLIENTE HTTP
# ═══════════════════════════════════════════════════════════════

def get_headers() -> Dict:
    api_key = st.secrets.get("FOOTBALL_API", "")
    if not api_key:
        raise ValueError("Falta FOOTBALL_API en Streamlit Secrets.")
    return {"x-apisports-key": api_key}

def _get(endpoint: str, params: Dict) -> Optional[Dict]:
    """
    Realiza 1 llamada GET a API-Sports.
    Maneja errores de autenticación, rate limit y conexión.
    """
    try:
        r = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers=get_headers(),
            params=params,
            timeout=15,
        )
        if r.status_code == 200:
            data   = r.json()
            errors = data.get("errors", {})
            if errors:
                msg = list(errors.values())[0] if isinstance(errors, dict) else str(errors)
                st.error(f"❌ Error API-Sports: {msg}")
                return None
            return data
        elif r.status_code == 429:
            st.warning("⚠️ Límite de 100 llamadas diarias alcanzado. Intenta mañana.")
            return None
        elif r.status_code == 401 or r.status_code == 403:
            st.error("❌ API Key inválida. Verifica FOOTBALL_API en Secrets.")
            return None
        else:
            st.error(f"❌ Error API: {r.status_code} — {r.text[:150]}")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# TRANSFORMADORES
# ═══════════════════════════════════════════════════════════════

def transformar_partido(fixture: Dict, competition: str, season: str) -> Dict:
    """
    Convierte un fixture del formato API-Sports
    al formato de nuestra tabla 'partidos' en Supabase.
    """
    fix    = fixture.get("fixture", {})
    teams  = fixture.get("teams",   {})
    score  = fixture.get("score",   {})
    league = fixture.get("league",  {})
    status_short = fix.get("status", {}).get("short", "NS")

    # Goles solo si el partido terminó
    terminado = status_short in ("FT", "AET", "PEN", "AWD", "WO")
    ft = score.get("fulltime", {})
    hg = ft.get("home") if terminado else None
    ag = ft.get("away") if terminado else None

    return {
        "api_match_id": str(fix.get("id", "")),
        "competition":  competition,
        "season":       season,
        "matchday":     league.get("round", ""),
        "fecha":        fix.get("date", ""),
        "home_team":    teams.get("home", {}).get("name", ""),
        "away_team":    teams.get("away", {}).get("name", ""),
        "home_goals":   hg,
        "away_goals":   ag,
        "status":       STATUS_MAP.get(status_short, "scheduled"),
    }

# ═══════════════════════════════════════════════════════════════
# LLAMADAS A LA API (cada función = 1 llamada)
# ═══════════════════════════════════════════════════════════════

def fetch_fixtures(league_id: int, season: str, status: str = None) -> Optional[List]:
    """
    Trae todos los fixtures de una liga/temporada.
    COSTO: 1 llamada.
    """
    params = {"league": league_id, "season": season}
    if status:
        params["status"] = status
    data = _get("fixtures", params)
    if data is None:
        return None
    return data.get("response", [])

def fetch_fixture_por_id(fixture_id: int) -> Optional[Dict]:
    """
    Trae detalle de un partido específico.
    COSTO: 1 llamada. Usar con moderación.
    """
    data = _get("fixtures", {"id": fixture_id})
    if data and data.get("response"):
        return data["response"][0]
    return None

def verificar_llamadas_restantes() -> Optional[int]:
    """
    Verifica cuántas llamadas quedan hoy.
    COSTO: 1 llamada (usarla con moderación).
    """
    data = _get("status", {})
    if data and data.get("response"):
        sub = data["response"].get("subscription", {})
        req = sub.get("requests", {})
        limite  = req.get("limit_day", 100)
        usadas  = req.get("current", 0)
        return limite - usadas
    return None

# ═══════════════════════════════════════════════════════════════
# SINCRONIZACIÓN
# ═══════════════════════════════════════════════════════════════

def sincronizar_competicion(nombre: str, league_id, season: str) -> Dict:
    """
    Descarga TODOS los partidos de una competición y los guarda en Supabase.
    COSTO: 1 llamada a la API.
    """
    try:
        lid = int(league_id)
    except (TypeError, ValueError):
        return {"ok": False, "mensaje": f"ID de liga inválido: {league_id}"}

    if not lid:
        return {"ok": False, "mensaje": "ID de liga no encontrado."}

    fixtures = fetch_fixtures(lid, season)
    if fixtures is None:
        return {"ok": False, "mensaje": "No se pudo conectar con API-Sports."}
    if not fixtures:
        return {"ok": False, "mensaje": f"No hay partidos para {nombre} temporada {season}. La liga podría no haber iniciado."}

    partidos   = [transformar_partido(f, nombre, season) for f in fixtures]
    procesados = bd.upsert_partidos_bulk(partidos)

    finalizados = sum(1 for p in partidos if p["status"] == "finished")
    programados = sum(1 for p in partidos if p["status"] == "scheduled")

    return {
        "ok":          True,
        "total":       len(partidos),
        "procesados":  procesados,
        "finalizados": finalizados,
        "programados": programados,
        "mensaje":     f"✅ {procesados} partidos guardados — {finalizados} finalizados, {programados} próximos.",
    }

def actualizar_resultados(nombre: str, league_id, season: str) -> Dict:
    """
    Actualiza solo los resultados de partidos finalizados.
    Más eficiente que sincronizar todo.
    COSTO: 1 llamada a la API.
    """
    try:
        lid = int(league_id)
    except (TypeError, ValueError):
        return {"ok": False, "mensaje": "ID de liga inválido."}

    fixtures = fetch_fixtures(lid, season, status="FT")
    if fixtures is None:
        return {"ok": False, "mensaje": "No se pudo obtener resultados."}

    actualizados = 0
    for f in fixtures:
        fix   = f.get("fixture", {})
        score = f.get("score", {}).get("fulltime", {})
        hg    = score.get("home")
        ag    = score.get("away")
        if hg is not None and ag is not None:
            ok = bd.actualizar_resultado_partido(str(fix.get("id", "")), int(hg), int(ag))
            if ok:
                actualizados += 1

    return {
        "ok":           True,
        "actualizados": actualizados,
        "mensaje":      f"✅ {actualizados} resultados actualizados.",
    }

# ═══════════════════════════════════════════════════════════════
# CONSULTAS LOCALES (sin llamadas a la API)
# ═══════════════════════════════════════════════════════════════

def get_partidos_para_modelo(competition: str, season: str) -> List[Dict]:
    """
    Retorna partidos finalizados para entrenar el modelo Dixon-Coles.
    SIN llamada a la API — lee directo desde Supabase.
    """
    partidos = bd.get_partidos_terminados(competition, season)
    return [
        p for p in partidos
        if p.get("home_goals") is not None
        and p.get("away_goals") is not None
    ]

def get_proximos_para_predecir(competition: str) -> List[Dict]:
    """
    Retorna los próximos partidos programados para generar predicciones.
    SIN llamada a la API.
    """
    return bd.get_proximos_partidos(competition, limit=10)

def get_estado_sincronizacion(competition: str, season: str) -> Dict:
    """
    Estado actual de datos en Supabase para una competición.
    SIN llamada a la API.
    """
    conteo = bd.contar_partidos(competition, season)
    return {
        "competition":       competition,
        "season":            season,
        "total":             conteo["total"],
        "finalizados":       conteo["finished"],
        "pendientes":        conteo["scheduled"],
        "listo_para_modelo": conteo["finished"] >= 5,
    }

# ═══════════════════════════════════════════════════════════════
# ATAJOS POR COMPETICIÓN
# ═══════════════════════════════════════════════════════════════

def sincronizar_mundial() -> Dict:
    """Copa del Mundo 2026. COSTO: 1 llamada."""
    return sincronizar_competicion(
        "FIFA World Cup",
        COMPETICIONES["FIFA World Cup"],
        TEMPORADA_MUNDIAL,
    )

def actualizar_resultados_mundial() -> Dict:
    """Actualiza resultados del Mundial. COSTO: 1 llamada."""
    return actualizar_resultados(
        "FIFA World Cup",
        COMPETICIONES["FIFA World Cup"],
        TEMPORADA_MUNDIAL,
    )

def sincronizar_liga(nombre_liga: str) -> Dict:
    """Sincroniza una liga europea. COSTO: 1 llamada."""
    lid = COMPETICIONES.get(nombre_liga)
    if not lid:
        return {"ok": False, "mensaje": f"Liga '{nombre_liga}' no encontrada."}
    return sincronizar_competicion(nombre_liga, lid, TEMPORADA_LIGAS)

# ═══════════════════════════════════════════════════════════════
# GESTIÓN DE LLAMADAS
# ═══════════════════════════════════════════════════════════════

def plan_llamadas_diario() -> Dict:
    return {
        "limite_diario":             100,
        "llamadas_reservadas":         2,
        "llamadas_disponibles_extras": 98,
        "uso_recomendado": [
            "1 llamada: sincronizar_competicion() — poblar BD",
            "1 llamada: actualizar_resultados()  — resultados del día",
            "98 restantes: margen de seguridad",
        ],
    }
