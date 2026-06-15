"""
gemini.py — Análisis de Contexto con IA (Gemini)
Enriquece las predicciones estadísticas de Dixon-Coles con información
cualitativa actual: lesiones, alineaciones, forma reciente, motivación.
Usa Google Search grounding para datos en tiempo real.
"""

from google import genai
from google.genai import types
import streamlit as st
import json
import re
from typing import Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# CLIENTE Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

MODELO = "gemini-3.5-flash"   # Flash completo para mejor razonamiento con búsqueda
MODELO_LITE = "gemini-3.1-flash-lite"  # Lite para tareas simples (más barato)

def get_client() -> genai.Client:
    api_key = st.secrets.get("GEMINI_API", "")
    if not api_key:
        raise ValueError("Falta GEMINI_API en Streamlit Secrets.")
    return genai.Client(api_key=api_key)

def _config_busqueda(temperatura: float = 0.1) -> types.GenerateContentConfig:
    """Config con Google Search grounding para información en tiempo real."""
    return types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=temperatura,
    )

def _config_json(temperatura: float = 0.0) -> types.GenerateContentConfig:
    """Config para respuestas JSON estructuradas (sin búsqueda)."""
    return types.GenerateContentConfig(
        temperature=temperatura,
        response_mime_type="application/json",
        max_output_tokens=2048,
    )

def _limpiar_json(texto: str) -> str:
    """Limpia bloques markdown de una respuesta JSON."""
    return re.sub(r"```json|```", "", texto).strip()

# ═══════════════════════════════════════════════════════════════
# ANÁLISIS DE CONTEXTO DE PARTIDO
# ═══════════════════════════════════════════════════════════════

def analizar_contexto_partido(
    home:        str,
    away:        str,
    competition: str,
    prediccion:  Dict = None,
) -> Optional[Dict]:
    """
    Análisis completo del contexto de un partido con búsqueda web.
    Retorna factores cualitativos que pueden afectar el resultado.
    Incluye sugerencia de ajuste a las probabilidades del modelo.
    1 llamada a Gemini con Google Search.
    """
    try:
        client = get_client()

        # Contexto de la predicción estadística si está disponible
        pred_txt = ""
        if prediccion:
            pred_txt = f"""
El modelo estadístico Dixon-Coles predice:
- Probabilidad victoria {home}: {prediccion.get('prob_home', 0)*100:.1f}%
- Probabilidad empate: {prediccion.get('prob_draw', 0)*100:.1f}%
- Probabilidad victoria {away}: {prediccion.get('prob_away', 0)*100:.1f}%
- Goles esperados: {prediccion.get('lambda_home', 0):.2f} - {prediccion.get('lambda_away', 0):.2f}
- Marcador más probable: {prediccion.get('marcador_probable', 'N/D')}
"""

        prompt = f"""
Eres un analista experto en {competition}. Busca información actualizada sobre:

PARTIDO: {home} vs {away} ({competition})
{pred_txt}

Investiga y responde con este JSON exacto (sin texto extra ni markdown):
{{
    "home_team": "{home}",
    "away_team": "{away}",
    "lesiones_home": {{
        "jugadores": [],
        "impacto": "alto|medio|bajo|ninguno",
        "detalle": "descripción breve"
    }},
    "lesiones_away": {{
        "jugadores": [],
        "impacto": "alto|medio|bajo|ninguno",
        "detalle": "descripción breve"
    }},
    "forma_home": {{
        "ultimos_5": "VVDED",
        "tendencia": "ascendente|estable|descendente",
        "detalle": "descripción breve"
    }},
    "forma_away": {{
        "ultimos_5": "VDVDP",
        "tendencia": "ascendente|estable|descendente",
        "detalle": "descripción breve"
    }},
    "factores_extra": [
        "factor relevante 1",
        "factor relevante 2"
    ],
    "ajuste_sugerido": {{
        "direccion": "home|draw|away|sin_cambio",
        "magnitud": "pequeño|moderado|grande",
        "razon": "por qué ajustar en esa dirección"
    }},
    "confianza_modelo": "alta|media|baja",
    "resumen": "análisis del partido en 2-3 oraciones",
    "fuente_info": "actualizada|limitada|sin_datos"
}}
"""
        resp = client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=_config_busqueda(temperatura=0.1),
        )

        # Extraer JSON de la respuesta (puede venir con texto adicional)
        texto = resp.text or ""
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None

    except json.JSONDecodeError as e:
        print(f"[gemini] JSON inválido en analizar_contexto: {e}")
        return None
    except Exception as e:
        print(f"[gemini] Error analizar_contexto_partido: {e}")
        return None

def buscar_alineacion_probable(home: str, away: str, competition: str) -> Optional[Dict]:
    """
    Busca las alineaciones probables o confirmadas para el partido.
    Muy útil las horas previas al partido.
    1 llamada a Gemini con Google Search.
    """
    try:
        client = get_client()
        prompt = f"""
Busca las alineaciones probables o confirmadas para:
{home} vs {away} en {competition}

Responde SOLO con este JSON:
{{
    "home_once": ["Jugador1", "Jugador2", "Jugador3"],
    "away_once": ["Jugador1", "Jugador2", "Jugador3"],
    "home_sistema": "4-3-3",
    "away_sistema": "4-4-2",
    "confirmadas": true,
    "fuente": "oficial|probable|sin_datos",
    "hora_confirmacion": "HH:MM o null"
}}

Si no hay información, usa listas vacías y fuente "sin_datos".
"""
        resp = client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=_config_busqueda(temperatura=0.0),
        )
        texto = resp.text or ""
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None

    except Exception as e:
        print(f"[gemini] Error buscar_alineacion: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# AJUSTE DE PROBABILIDADES
# ═══════════════════════════════════════════════════════════════

FACTORES_AJUSTE = {
    # (dirección, magnitud) → multiplicador para esa probabilidad
    ("home",  "pequeño"):   {"home": 1.05, "draw": 0.98, "away": 0.94},
    ("home",  "moderado"):  {"home": 1.10, "draw": 0.96, "away": 0.88},
    ("home",  "grande"):    {"home": 1.18, "draw": 0.93, "away": 0.80},
    ("away",  "pequeño"):   {"home": 0.94, "draw": 0.98, "away": 1.05},
    ("away",  "moderado"):  {"home": 0.88, "draw": 0.96, "away": 1.10},
    ("away",  "grande"):    {"home": 0.80, "draw": 0.93, "away": 1.18},
    ("draw",  "pequeño"):   {"home": 0.97, "draw": 1.06, "away": 0.97},
    ("draw",  "moderado"):  {"home": 0.93, "draw": 1.12, "away": 0.93},
    ("sin_cambio", "pequeño"):  {"home": 1.0, "draw": 1.0, "away": 1.0},
    ("sin_cambio", "moderado"): {"home": 1.0, "draw": 1.0, "away": 1.0},
    ("sin_cambio", "grande"):   {"home": 1.0, "draw": 1.0, "away": 1.0},
}

def ajustar_prediccion(prediccion: Dict, contexto: Dict) -> Dict:
    """
    Ajusta las probabilidades del modelo con el contexto cualitativo.
    Los ajustes son conservadores — el modelo estadístico tiene prioridad.
    Retorna predicción ajustada con las probabilidades corregidas.
    """
    if not contexto or not prediccion:
        return prediccion

    ajuste = contexto.get("ajuste_sugerido", {})
    dir_   = ajuste.get("direccion", "sin_cambio")
    mag    = ajuste.get("magnitud", "pequeño")
    key    = (dir_, mag)

    factores = FACTORES_AJUSTE.get(key, {"home": 1.0, "draw": 1.0, "away": 1.0})

    # Aplicar ajuste
    p_home = prediccion["prob_home"] * factores["home"]
    p_draw = prediccion["prob_draw"] * factores["draw"]
    p_away = prediccion["prob_away"] * factores["away"]

    # Renormalizar para que sumen 1
    total  = p_home + p_draw + p_away
    p_home /= total
    p_draw /= total
    p_away /= total

    pred_ajustada = prediccion.copy()
    pred_ajustada.update({
        "prob_home":         round(p_home, 4),
        "prob_draw":         round(p_draw, 4),
        "prob_away":         round(p_away, 4),
        "prob_home_original":prediccion["prob_home"],
        "prob_draw_original":prediccion["prob_draw"],
        "prob_away_original":prediccion["prob_away"],
        "ajuste_aplicado":   key,
        "razon_ajuste":      ajuste.get("razon", ""),
        "confianza_modelo":  contexto.get("confianza_modelo", "media"),
    })
    return pred_ajustada

# ═══════════════════════════════════════════════════════════════
# GENERADOR DE BOLETOS INTELIGENTE
# ═══════════════════════════════════════════════════════════════

def generar_boleto_inteligente(
    picks_valor:  List[Dict],
    competition:  str,
    bankroll:     float = 100.0,
) -> Optional[Dict]:
    """
    Toma los picks con +EV del modelo y genera boletos optimizados.
    Incluye narrativa explicativa para cada pick.
    No usa búsqueda web — trabaja con los datos ya disponibles.
    1 llamada a Gemini (sin Search).
    """
    if not picks_valor:
        return None
    try:
        client = get_client()
        picks_txt = json.dumps(picks_valor, ensure_ascii=False, indent=2)

        prompt = f"""
Eres un analista experto en apuestas de valor. Tienes estos picks con valor esperado positivo (+EV) 
detectados por el modelo Dixon-Coles para {competition}:

{picks_txt}

Bankroll disponible: ${bankroll}

Construye 3 boletos optimizados (seguro, moderado, arriesgado) seleccionando los mejores picks.

REGLA ANTI-CORRELACIÓN: No combines victoria directa y hándicap del mismo partido.
REGLA KELLY: Usa el campo kelly_pct para dimensionar las apuestas.

Responde ÚNICAMENTE con este JSON (sin texto extra):
{{
    "resumen_valor": "Por qué estos picks tienen valor en 1-2 oraciones.",
    "boleto_seguro": {{
        "tipo": "segura",
        "picks": [
            {{
                "partido": "Local vs Visitante",
                "mercado": "1X2",
                "seleccion": "Local",
                "cuota": 1.85,
                "ev_pct": 7.2,
                "razon": "Por qué este pick tiene valor"
            }}
        ],
        "cuota_total": 1.85,
        "apuesta_sugerida": 15.0,
        "ganancia_potencial": 12.75,
        "descripcion": "Descripción de la estrategia"
    }},
    "boleto_moderado": {{
        "tipo": "moderada",
        "picks": [],
        "cuota_total": 3.20,
        "apuesta_sugerida": 8.0,
        "ganancia_potencial": 17.60,
        "descripcion": "Descripción de la estrategia"
    }},
    "boleto_arriesgado": {{
        "tipo": "arriesgada",
        "picks": [],
        "cuota_total": 6.50,
        "apuesta_sugerida": 4.0,
        "ganancia_potencial": 22.00,
        "descripcion": "Descripción de la estrategia"
    }}
}}
"""
        resp = client.models.generate_content(
            model=MODELO_LITE,
            contents=prompt,
            config=_config_json(temperatura=0.1),
        )
        raw = _limpiar_json(resp.text or "")
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"[gemini] JSON inválido en generar_boleto: {e}")
        return None
    except Exception as e:
        print(f"[gemini] Error generar_boleto_inteligente: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# REPORTE DIARIO
# ═══════════════════════════════════════════════════════════════

def generar_reporte_diario(
    competition: str,
    partidos:    List[Dict],
) -> Optional[str]:
    """
    Genera un reporte ejecutivo diario con los mejores picks del día.
    Incluye análisis de valor y recomendaciones de bankroll.
    1 llamada a Gemini con Google Search.
    """
    if not partidos:
        return None
    try:
        client  = get_client()
        resumen = []
        for p in partidos:
            partido   = p.get("partido", {})
            prediccion = p.get("prediccion", {})
            picks     = p.get("picks", [])
            resumen.append({
                "partido":    f"{partido.get('home_team')} vs {partido.get('away_team')}",
                "fecha":      partido.get("fecha", ""),
                "prob_home":  f"{prediccion.get('prob_home', 0)*100:.1f}%",
                "prob_draw":  f"{prediccion.get('prob_draw', 0)*100:.1f}%",
                "prob_away":  f"{prediccion.get('prob_away', 0)*100:.1f}%",
                "picks_ev":   len(picks),
                "mejor_pick": picks[0]["seleccion"] if picks else "Sin valor",
                "mejor_ev":   f"{picks[0]['valor_esperado']:.1f}%" if picks else "0%",
            })

        prompt = f"""
Genera un reporte ejecutivo diario de apuestas para {competition}.

ANÁLISIS DEL MODELO:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

Busca noticias relevantes del día para contextualizar.

El reporte debe incluir:
1. Resumen ejecutivo (2-3 oraciones)
2. Mejor pick del día con justificación
3. Advertencias o factores de riesgo
4. Recomendación de bankroll (% a arriesgar hoy)

Escribe en español, tono profesional pero directo. Máximo 200 palabras.
"""
        resp = client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=_config_busqueda(temperatura=0.2),
        )
        return resp.text.strip() if resp.text else None

    except Exception as e:
        print(f"[gemini] Error generar_reporte_diario: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# ANÁLISIS POST-PARTIDO (MEJORA DEL MODELO)
# ═══════════════════════════════════════════════════════════════

def analizar_resultado_posterior(
    home:       str,
    away:       str,
    resultado:  str,
    prediccion: Dict,
    contexto:   Dict = None,
) -> Optional[Dict]:
    """
    Analiza por qué el modelo acertó o falló en un partido.
    Genera insights para mejorar el modelo a futuro.
    Sin búsqueda web — análisis basado en los datos del partido.
    """
    try:
        client = get_client()
        prompt = f"""
Analiza el resultado de este partido para mejorar el modelo de predicción.

PARTIDO: {home} vs {away}
RESULTADO REAL: {resultado}
PREDICCIÓN DEL MODELO:
- Prob. victoria {home}: {prediccion.get('prob_home', 0)*100:.1f}%
- Prob. empate: {prediccion.get('prob_draw', 0)*100:.1f}%
- Prob. victoria {away}: {prediccion.get('prob_away', 0)*100:.1f}%
- Goles esperados: {prediccion.get('lambda_home', 0):.2f} - {prediccion.get('lambda_away', 0):.2f}

CONTEXTO CUALITATIVO PREVIO:
{json.dumps(contexto, ensure_ascii=False) if contexto else 'No disponible'}

Responde SOLO con este JSON:
{{
    "modelo_acerto": true,
    "error_magnitud": "ninguno|pequeño|moderado|grande",
    "causa_error": "descripción si falló, o null si acertó",
    "factor_no_capturado": "qué variable influyó que el modelo no considera",
    "aprendizaje": "qué ajuste mejoraría el modelo para casos similares",
    "tipo_error": "suerte|datos_insuficientes|factor_externo|modelo_limitado|null"
}}
"""
        resp = client.models.generate_content(
            model=MODELO_LITE,
            contents=prompt,
            config=_config_json(temperatura=0.0),
        )
        raw = _limpiar_json(resp.text or "")
        return json.loads(raw)

    except Exception as e:
        print(f"[gemini] Error analizar_resultado_posterior: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# VERIFICADOR AUTOMÁTICO DE RESULTADOS
# ═══════════════════════════════════════════════════════════════

def verificar_picks_pendientes(picks: List[Dict]) -> List[Dict]:
    """
    Verifica el resultado de picks pendientes usando búsqueda web.
    Más preciso que solo depender de la API de scores.
    Retorna lista con resultado actualizado para cada pick.
    """
    if not picks:
        return []
    try:
        client = get_client()
        picks_txt = json.dumps([{
            "id":        p.get("id"),
            "partido":   f"{p.get('home_team')} vs {p.get('away_team')}",
            "mercado":   p.get("mercado"),
            "seleccion": p.get("seleccion"),
            "fecha":     str(p.get("fecha", ""))[:10],
        } for p in picks], ensure_ascii=False, indent=2)

        prompt = f"""
Busca los resultados finales de estos partidos y evalúa cada apuesta:

{picks_txt}

Para cada pick, determina si se ganó o perdió según el resultado real.

Responde SOLO con este JSON:
{{
    "resultados": [
        {{
            "id": 1,
            "resultado_partido": "2-1",
            "pick_resultado": "acertado|fallido|pendiente",
            "razon": "por qué acertó/falló"
        }}
    ]
}}
"""
        resp = client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=_config_busqueda(temperatura=0.0),
        )
        texto = resp.text or ""
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data.get("resultados", [])
        return []

    except Exception as e:
        print(f"[gemini] Error verificar_picks_pendientes: {e}")
        return []
