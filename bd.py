"""
bd.py — Módulo de Base de Datos (Supabase)
Todas las operaciones de lectura/escritura del sistema de predicción.
"""

from supabase import create_client, Client
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import streamlit as st

# ═══════════════════════════════════════════════════════════════
# CONEXIÓN
# ═══════════════════════════════════════════════════════════════

def get_client() -> Client:
    """Retorna cliente Supabase usando las credenciales de Streamlit Secrets."""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise ValueError("Faltan credenciales SUPABASE_URL o SUPABASE_KEY en secrets.")
    return create_client(url, key)

# ═══════════════════════════════════════════════════════════════
# PARTIDOS
# ═══════════════════════════════════════════════════════════════

def upsert_partido(partido: Dict) -> Optional[Dict]:
    """
    Inserta o actualiza un partido por api_match_id.
    Si ya existe lo actualiza (útil para sincronizar resultados).
    """
    try:
        sb = get_client()
        partido["updated_at"] = datetime.now().isoformat()
        res = sb.table("partidos").upsert(
            partido, on_conflict="api_match_id"
        ).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error upsert_partido: {e}")
        return None

def upsert_partidos_bulk(partidos: List[Dict]) -> int:
    """Inserta/actualiza múltiples partidos de una vez. Retorna cantidad procesada."""
    try:
        sb = get_client()
        now = datetime.now().isoformat()
        for p in partidos:
            p["updated_at"] = now
        res = sb.table("partidos").upsert(
            partidos, on_conflict="api_match_id"
        ).execute()
        return len(res.data) if res.data else 0
    except Exception as e:
        print(f"[bd] Error upsert_partidos_bulk: {e}")
        return 0

def get_partidos_terminados(competition: str, season: str) -> List[Dict]:
    """Retorna todos los partidos finalizados de una competición/temporada."""
    try:
        sb = get_client()
        return (
            sb.table("partidos")
            .select("*")
            .eq("competition", competition)
            .eq("season", season)
            .eq("status", "finished")
            .order("fecha")
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error get_partidos_terminados: {e}")
        return []

def get_proximos_partidos(competition: str, limit: int = 10) -> List[Dict]:
    """Retorna los próximos partidos programados de una competición."""
    try:
        sb = get_client()
        hoy = date.today().isoformat()
        return (
            sb.table("partidos")
            .select("*")
            .eq("competition", competition)
            .eq("status", "scheduled")
            .gte("fecha", hoy)
            .order("fecha")
            .limit(limit)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error get_proximos_partidos: {e}")
        return []

def get_partido_por_id(partido_id: int) -> Optional[Dict]:
    """Retorna un partido por su ID interno."""
    try:
        sb = get_client()
        res = sb.table("partidos").select("*").eq("id", partido_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error get_partido_por_id: {e}")
        return None

def actualizar_resultado_partido(api_match_id: str, home_goals: int, away_goals: int) -> bool:
    """Actualiza el resultado final de un partido."""
    try:
        sb = get_client()
        sb.table("partidos").update({
            "home_goals":  home_goals,
            "away_goals":  away_goals,
            "status":      "finished",
            "updated_at":  datetime.now().isoformat(),
        }).eq("api_match_id", api_match_id).execute()
        return True
    except Exception as e:
        print(f"[bd] Error actualizar_resultado_partido: {e}")
        return False

def get_competiciones_disponibles() -> List[str]:
    """Retorna lista de competiciones que tienen partidos en BD."""
    try:
        sb = get_client()
        res = sb.table("partidos").select("competition").execute()
        return list(set(p["competition"] for p in res.data)) if res.data else []
    except Exception as e:
        print(f"[bd] Error get_competiciones: {e}")
        return []

def contar_partidos(competition: str, season: str) -> Dict:
    """Retorna conteo de partidos por estado para una competición."""
    try:
        sb   = get_client()
        todos = (
            sb.table("partidos")
            .select("status")
            .eq("competition", competition)
            .eq("season", season)
            .execute()
            .data
        )
        return {
            "total":      len(todos),
            "finished":   sum(1 for p in todos if p["status"] == "finished"),
            "scheduled":  sum(1 for p in todos if p["status"] == "scheduled"),
        }
    except Exception as e:
        print(f"[bd] Error contar_partidos: {e}")
        return {"total": 0, "finished": 0, "scheduled": 0}

# ═══════════════════════════════════════════════════════════════
# EQUIPOS
# ═══════════════════════════════════════════════════════════════

def upsert_equipo(equipo: Dict) -> Optional[Dict]:
    """
    Inserta o actualiza parámetros del modelo para un equipo.
    Clave única: (competition, season, team_name).
    """
    try:
        sb = get_client()
        equipo["updated_at"] = datetime.now().isoformat()
        res = sb.table("equipos").upsert(
            equipo, on_conflict="competition,season,team_name"
        ).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error upsert_equipo: {e}")
        return None

def upsert_equipos_bulk(equipos: List[Dict]) -> int:
    """Actualiza parámetros de múltiples equipos en una sola operación."""
    try:
        sb  = get_client()
        now = datetime.now().isoformat()
        for e in equipos:
            e["updated_at"] = now
        res = sb.table("equipos").upsert(
            equipos, on_conflict="competition,season,team_name"
        ).execute()
        return len(res.data) if res.data else 0
    except Exception as e:
        print(f"[bd] Error upsert_equipos_bulk: {e}")
        return 0

def get_equipos(competition: str, season: str) -> List[Dict]:
    """Retorna todos los equipos con sus parámetros del modelo."""
    try:
        sb = get_client()
        return (
            sb.table("equipos")
            .select("*")
            .eq("competition", competition)
            .eq("season", season)
            .order("team_name")
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error get_equipos: {e}")
        return []

def get_equipo(competition: str, season: str, team_name: str) -> Optional[Dict]:
    """Retorna los parámetros del modelo para un equipo específico."""
    try:
        sb  = get_client()
        res = (
            sb.table("equipos")
            .select("*")
            .eq("competition", competition)
            .eq("season", season)
            .eq("team_name", team_name)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error get_equipo: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# PREDICCIONES
# ═══════════════════════════════════════════════════════════════

def guardar_prediccion(prediccion: Dict) -> Optional[Dict]:
    """Guarda una nueva predicción del modelo para un partido."""
    try:
        sb  = get_client()
        res = sb.table("predicciones").insert(prediccion).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error guardar_prediccion: {e}")
        return None

def get_prediccion_por_partido(partido_id: int) -> Optional[Dict]:
    """Retorna la predicción más reciente para un partido dado."""
    try:
        sb  = get_client()
        res = (
            sb.table("predicciones")
            .select("*")
            .eq("partido_id", partido_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error get_prediccion_por_partido: {e}")
        return None

def get_predicciones_recientes(competition: str, limit: int = 20) -> List[Dict]:
    """Retorna las predicciones más recientes de una competición."""
    try:
        sb = get_client()
        return (
            sb.table("predicciones")
            .select("*")
            .eq("competition", competition)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error get_predicciones_recientes: {e}")
        return []

def get_predicciones_proximos_partidos(competition: str) -> List[Dict]:
    """
    Retorna predicciones de partidos aún no jugados.
    Útil para mostrar las apuestas recomendadas del día.
    """
    try:
        sb   = get_client()
        hoy  = date.today().isoformat()
        return (
            sb.table("predicciones")
            .select("*, partidos(status, home_goals, away_goals)")
            .eq("competition", competition)
            .gte("fecha", hoy)
            .order("fecha")
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error get_predicciones_proximos: {e}")
        return []

# ═══════════════════════════════════════════════════════════════
# VALOR DETECTADO (+EV)
# ═══════════════════════════════════════════════════════════════

def guardar_valor(valor: Dict) -> Optional[Dict]:
    """Guarda un pick con valor esperado positivo detectado."""
    try:
        sb  = get_client()
        res = sb.table("valor_detectado").insert(valor).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[bd] Error guardar_valor: {e}")
        return None

def guardar_valores_bulk(valores: List[Dict]) -> int:
    """Guarda múltiples picks de valor de una vez."""
    try:
        sb  = get_client()
        res = sb.table("valor_detectado").insert(valores).execute()
        return len(res.data) if res.data else 0
    except Exception as e:
        print(f"[bd] Error guardar_valores_bulk: {e}")
        return 0

def get_valores_pendientes(competition: str = None) -> List[Dict]:
    """Retorna todos los picks pendientes de resultado."""
    try:
        sb = get_client()
        q  = sb.table("valor_detectado").select("*").eq("resultado", "pendiente")
        if competition:
            q = q.eq("competition", competition)
        return q.order("fecha").execute().data
    except Exception as e:
        print(f"[bd] Error get_valores_pendientes: {e}")
        return []

def get_valores_por_competicion(competition: str, limit: int = 50) -> List[Dict]:
    """Retorna el historial completo de picks de una competición."""
    try:
        sb = get_client()
        return (
            sb.table("valor_detectado")
            .select("*")
            .eq("competition", competition)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error get_valores_por_competicion: {e}")
        return []

def actualizar_resultado_valor(valor_id: int, resultado: str) -> bool:
    """Actualiza si un pick acertó o falló (acertado | fallido)."""
    try:
        sb = get_client()
        sb.table("valor_detectado").update(
            {"resultado": resultado}
        ).eq("id", valor_id).execute()
        return True
    except Exception as e:
        print(f"[bd] Error actualizar_resultado_valor: {e}")
        return False

def actualizar_resultados_bulk(partido_id: int, resultado_real: str) -> bool:
    """
    Actualiza todos los picks de un partido de golpe
    cuando se conoce el resultado final.
    resultado_real: 'home' | 'draw' | 'away'
    """
    try:
        sb     = get_client()
        picks  = (
            sb.table("valor_detectado")
            .select("id, seleccion")
            .eq("partido_id", partido_id)
            .eq("resultado", "pendiente")
            .execute()
            .data
        )
        mapa = {"Local": "home", "Empate": "draw", "Visitante": "away"}
        for pick in picks:
            acerto = mapa.get(pick["seleccion"]) == resultado_real
            sb.table("valor_detectado").update(
                {"resultado": "acertado" if acerto else "fallido"}
            ).eq("id", pick["id"]).execute()
        return True
    except Exception as e:
        print(f"[bd] Error actualizar_resultados_bulk: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
# ESTADÍSTICAS DEL MODELO
# ═══════════════════════════════════════════════════════════════

def get_estadisticas_modelo(competition: str = None) -> Dict:
    """
    Calcula hit rate y ROI real del modelo.
    Si no se especifica competition, calcula globalmente.
    """
    try:
        sb = get_client()
        q  = sb.table("valor_detectado").select("*").neq("resultado", "pendiente")
        if competition:
            q = q.eq("competition", competition)
        todos = q.execute().data

        if not todos:
            return {
                "total": 0, "acertados": 0, "fallidos": 0,
                "hit_rate": 0.0, "roi": 0.0, "ev_promedio": 0.0,
            }

        acertados = [v for v in todos if v["resultado"] == "acertado"]
        fallidos  = [v for v in todos if v["resultado"] == "fallido"]
        total     = len(todos)
        n_acert   = len(acertados)

        # ROI asumiendo 1 unidad apostada por pick
        ganancia  = sum((v["cuota"] - 1) for v in acertados)
        perdida   = float(len(fallidos))
        roi       = ((ganancia - perdida) / total * 100) if total > 0 else 0.0

        # EV promedio de los picks seleccionados
        ev_prom   = sum(v["valor_esperado"] for v in todos) / total if total > 0 else 0.0

        return {
            "total":      total,
            "acertados":  n_acert,
            "fallidos":   len(fallidos),
            "hit_rate":   round(n_acert / total * 100, 1) if total > 0 else 0.0,
            "roi":        round(roi, 2),
            "ev_promedio": round(ev_prom * 100, 2),
        }
    except Exception as e:
        print(f"[bd] Error get_estadisticas_modelo: {e}")
        return {
            "total": 0, "acertados": 0, "fallidos": 0,
            "hit_rate": 0.0, "roi": 0.0, "ev_promedio": 0.0,
        }

def get_mejor_mercado(competition: str) -> List[Dict]:
    """
    Analiza qué mercados (1X2, Over/Under, etc.) tienen mejor ROI.
    Útil para calibrar el modelo.
    """
    try:
        sb    = get_client()
        todos = (
            sb.table("valor_detectado")
            .select("mercado, seleccion, cuota, resultado")
            .eq("competition", competition)
            .neq("resultado", "pendiente")
            .execute()
            .data
        )
        if not todos:
            return []

        # Agrupar por mercado
        mercados: Dict[str, Dict] = {}
        for v in todos:
            m = v["mercado"]
            if m not in mercados:
                mercados[m] = {"mercado": m, "total": 0, "acertados": 0, "ganancia": 0.0}
            mercados[m]["total"] += 1
            if v["resultado"] == "acertado":
                mercados[m]["acertados"] += 1
                mercados[m]["ganancia"]  += v["cuota"] - 1
            else:
                mercados[m]["ganancia"] -= 1

        resultado = []
        for m, d in mercados.items():
            resultado.append({
                "mercado":  m,
                "total":    d["total"],
                "acertados":d["acertados"],
                "hit_rate": round(d["acertados"] / d["total"] * 100, 1),
                "roi":      round(d["ganancia"] / d["total"] * 100, 2),
            })
        return sorted(resultado, key=lambda x: x["roi"], reverse=True)
    except Exception as e:
        print(f"[bd] Error get_mejor_mercado: {e}")
        return []

# ═══════════════════════════════════════════════════════════════
# BOLETOS (tabla historial — compatibilidad con app actual)
# ═══════════════════════════════════════════════════════════════

def guardar_ticket_db(liga: str, partidos_str: str, analisis_json: str) -> bool:
    """Guarda boleto generado por IA (compatible con tabla historial existente)."""
    import json
    from datetime import datetime
    try:
        sb = get_client()
        sb.table("historial").insert({
            "fecha_gen":    datetime.now().isoformat(),
            "liga":         liga,
            "partidos":     partidos_str,
            "analisis_json":analisis_json,
        }).execute()
        return True
    except Exception as e:
        print(f"[bd] Error guardar_ticket_db: {e}")
        return False

def cargar_historial_db(limit: int = 30) -> List[Dict]:
    """Carga historial de boletos generados."""
    try:
        sb = get_client()
        return (
            sb.table("historial")
            .select("*")
            .order("id", desc=True)
            .limit(limit)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[bd] Error cargar_historial_db: {e}")
        return []

def actualizar_resultado_historial(ticket_id: int, campo: str, valor: str) -> bool:
    """Actualiza resultado manual de un pick en el historial de boletos."""
    try:
        sb = get_client()
        sb.table("historial").update({campo: valor}).eq("id", ticket_id).execute()
        return True
    except Exception as e:
        print(f"[bd] Error actualizar_resultado_historial: {e}")
        return False

def eliminar_ticket_db(ticket_id: int) -> bool:
    """Elimina un boleto del historial."""
    try:
        sb = get_client()
        sb.table("historial").delete().eq("id", ticket_id).execute()
        return True
    except Exception as e:
        print(f"[bd] Error eliminar_ticket_db: {e}")
        return False