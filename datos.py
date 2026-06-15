"""
datos.py — Recolección de Datos (Football-Data.org)
Optimizado para 100 llamadas diarias del tier FREE.
Estrategia: mínimas llamadas, máximo dato guardado en Supabase.
"""

import requests
import streamlit as st
from datetime import datetime, date, timezone
from typing import Optional, List, Dict
import bd

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

BASE_URL = "https://api.football-data.org/v4"

# Competiciones disponibles en tier FREE y sus códigos
COMPETICIONES = {
    "FIFA World Cup":    "WC",
    "Premier League":    "PL",
    "La Liga":           "PD",
    "Serie A":           "SA",
    "Bundesliga":        "BL1",
    "Ligue 1":           "FL1",
}

# Temporadas
TEMPORADA_MUNDIAL  = "2026"
TEMPORADA_LIGAS    = "2025"

def get_headers() -> Dict:
    """Headers de autenticación para Football-Data.org."""
    api_key = st.secrets.get("FOOTBALL_API", "")
    if not api_key:
        raise ValueError("Falta FOOTBALL_API en Streamlit Secrets.")
    return {"X-Auth-Token": api_key}

# ═══════════════════════════════════════════════════════════════
# LLAMADAS A LA API (cada función = 1 llamada)
# ═══════════════════════════════════════════════════════════════

def fetch_partidos_competicion(codigo: str, temporada: str) -> Optional[Dict]:
    """
    Trae TODOS los partidos de una competición en una sola llamada.
    1 llamada = toda la competición.
    """
    try:
        url = f"{BASE_URL}/competitions/{codigo}/matches"
        params = {"season": temporada}
        r = requests.get(url, headers=get_headers(), params=params, timeout=15)

        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            st.warning("⚠️ Límite de llamadas diarias alcanzado. Intenta mañana.")
            return None
        elif r.status_code == 403:
            st.error("❌ API Key inválida o competición no disponible en tu plan.")
            return None
        else:
            st.error(f"❌ Error API: {r.status_code} — {r.text[:100]}")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def fetch_resultados_recientes(codigo: str, temporada: str) -> Optional[Dict]:
    """
    Trae solo los partidos FINALIZADOS para actualizar resultados.
    1 llamada = resultados del día.
    """
    try:
        url    = f"{BASE_URL}/competitions/{codigo}/matches"
        params = {"season": temporada, "status": "FINISHED"}
        r = requests.get(url, headers=get_headers(), params=params, timeout=15)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"[datos] Error fetch_resultados_recientes: {e}")
        return None

def fetch_partido_especifico(match_id: str) -> Optional[Dict]:
    """
    Trae detalle de un partido específico por su ID.
    Úsalo solo cuando necesites detalle de un partido puntual.
    1 llamada = 1 partido.
    """
    try:
        url = f"{BASE_URL}/matches/{match_id}"
        r   = requests.get(url, headers=get_headers(), timeout=15)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"[datos] Error fetch_partido_especifico: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# TRANSFORMADORES (API → formato BD)
# ═══════════════════════════════════════════════════════════════

def transformar_partido(match: Dict, competition: str, season: str) -> Dict:
    """
    Convierte un partido del formato de Football-Data.org
    al formato de nuestra tabla 'partidos' en Supabase.
    """
    score    = match.get("score", {})
    full     = score.get("fullTime", {})
    status   = match.get("status", "SCHEDULED")

    # Mapear status de la API a nuestro formato
    status_map = {
        "SCHEDULED":   "scheduled",
        "TIMED":       "scheduled",
        "IN_PLAY":     "in_play",
        "PAUSED":      "in_play",
        "FINISHED":    "finished",
        "POSTPONED":   "postponed",
        "CANCELLED":   "postponed",
        "SUSPENDED":   "postponed",
    }

    return {
        "api_match_id": str(match.get("id", "")),
        "competition":  competition,
        "season":       season,
        "matchday":     match.get("matchday"),
        "fecha":        match.get("utcDate", ""),
        "home_team":    match.get("homeTeam", {}).get("name", ""),
        "away_team":    match.get("awayTeam", {}).get("name", ""),
        "home_goals":   full.get("home"),     # None si no se jugó
        "away_goals":   full.get("away"),
        "status":       status_map.get(status, "scheduled"),
    }

# ═══════════════════════════════════════════════════════════════
# SINCRONIZACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def sincronizar_competicion(nombre: str, codigo: str, temporada: str) -> Dict:
    """
    Sincronización completa de una competición.
    Trae todos los partidos y los guarda/actualiza en Supabase.
    COSTO: 1 llamada a la API.
    Retorna resumen de lo que se procesó.
    """
    datos = fetch_partidos_competicion(codigo, temporada)
    if not datos:
        return {"ok": False, "mensaje": "No se pudo conectar con la API."}

    matches   = datos.get("matches", [])
    if not matches:
        return {"ok": False, "mensaje": "No hay partidos en esta competición/temporada."}

    partidos  = [transformar_partido(m, nombre, temporada) for m in matches]
    procesados = bd.upsert_partidos_bulk(partidos)

    return {
        "ok":         True,
        "total":      len(partidos),
        "procesados": procesados,
        "mensaje":    f"✅ {procesados} partidos sincronizados en Supabase.",
    }

def actualizar_resultados(nombre: str, codigo: str, temporada: str) -> Dict:
    """
    Actualiza solo los resultados de partidos finalizados.
    Más económico que sincronizar todo.
    COSTO: 1 llamada a la API.
    """
    datos = fetch_resultados_recientes(codigo, temporada)
    if not datos:
        return {"ok": False, "mensaje": "No se pudo obtener resultados."}

    matches     = datos.get("matches", [])
    actualizados = 0

    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        hg    = score.get("home")
        ag    = score.get("away")
        if hg is not None and ag is not None:
            ok = bd.actualizar_resultado_partido(str(m["id"]), hg, ag)
            if ok:
                actualizados += 1

    return {
        "ok":          True,
        "actualizados": actualizados,
        "mensaje":     f"✅ {actualizados} resultados actualizados.",
    }

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE CONSULTA (sin llamadas a la API — solo Supabase)
# ═══════════════════════════════════════════════════════════════

def get_partidos_para_modelo(competition: str, season: str) -> List[Dict]:
    """
    Retorna partidos finalizados listos para entrenar el modelo.
    Solo partidos con resultado completo.
    SIN llamada a la API — lee desde Supabase.
    """
    partidos = bd.get_partidos_terminados(competition, season)
    return [
        p for p in partidos
        if p.get("home_goals") is not None
        and p.get("away_goals") is not None
    ]

def get_proximos_para_predecir(competition: str) -> List[Dict]:
    """
    Retorna los próximos partidos sin resultado para generar predicciones.
    SIN llamada a la API — lee desde Supabase.
    """
    return bd.get_proximos_partidos(competition, limit=10)

def get_estado_sincronizacion(competition: str, season: str) -> Dict:
    """
    Muestra el estado actual de la BD para una competición.
    SIN llamada a la API.
    """
    conteo = bd.contar_partidos(competition, season)
    return {
        "competition": competition,
        "season":      season,
        "total":       conteo["total"],
        "finalizados": conteo["finished"],
        "pendientes":  conteo["scheduled"],
        "listo_para_modelo": conteo["finished"] >= 10,
    }

# ═══════════════════════════════════════════════════════════════
# GESTOR DE LLAMADAS (controla el gasto diario)
# ═══════════════════════════════════════════════════════════════

def sincronizar_mundial() -> Dict:
    """
    Sincronización específica del Mundial 2026.
    Llama una sola vez para poblar toda la BD.
    COSTO: 1 llamada.
    """
    return sincronizar_competicion("FIFA World Cup", "WC", TEMPORADA_MUNDIAL)

def actualizar_resultados_mundial() -> Dict:
    """
    Actualiza resultados del Mundial.
    Llamar una vez al día después de que terminen los partidos.
    COSTO: 1 llamada.
    """
    return actualizar_resultados("FIFA World Cup", "WC", TEMPORADA_MUNDIAL)

def sincronizar_liga(nombre_liga: str) -> Dict:
    """
    Sincroniza una liga específica.
    COSTO: 1 llamada.
    """
    codigo = COMPETICIONES.get(nombre_liga)
    if not codigo:
        return {"ok": False, "mensaje": f"Liga '{nombre_liga}' no encontrada."}
    return sincronizar_competicion(nombre_liga, codigo, TEMPORADA_LIGAS)

def plan_llamadas_diario() -> Dict:
    """
    Retorna el plan óptimo de llamadas para no superar el límite diario.
    Guía para el dashboard de administración.
    """
    return {
        "limite_diario":  100,
        "uso_recomendado": [
            {"llamada": 1, "funcion": "actualizar_resultados_mundial()",
             "descripcion": "Actualiza resultados del día anterior"},
            {"llamada": 2, "funcion": "get_proximos_para_predecir()",
             "descripcion": "Lee próximos partidos desde Supabase (gratis)"},
            {"llamada": 3, "funcion": "modelo.py genera predicciones",
             "descripcion": "Cálculo local, sin API (gratis)"},
        ],
        "llamadas_reservadas": 3,
        "llamadas_disponibles_extras": 97,
        "nota": "Las 97 restantes son margen de seguridad y para sincronizaciones manuales.",
    }
