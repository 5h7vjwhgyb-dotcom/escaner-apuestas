import streamlit as st
import requests
from google import genai
from google.genai import types

# ─────────────────────────────────────────
# DISEÑO Y CONFIGURACIÓN
# ─────────────────────────────────────────
st.set_page_config(page_title="Elite Analytics Pro", layout="wide")
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }
    .card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        padding: 20px;
        border-radius: 20px;
        border-left: 6px solid #00ff9d;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    h3 { color: #00ff9d !important; font-size: 1.2rem; }
    .stButton > button {
        background: linear-gradient(90deg, #00ff9d, #00d2ff);
        border: none;
        border-radius: 12px;
        font-weight: bold;
        width: 100%;
        color: #0f0c29;
        font-size: 1rem;
        padding: 0.6em 1em;
    }
    .stTextInput input, .stTextArea textarea {
        background: rgba(255,255,255,0.07) !important;
        color: white !important;
        border-radius: 10px !important;
    }
    .info-box {
        background: rgba(0,255,157,0.1);
        border: 1px solid #00ff9d;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 0.9rem;
    }
    .quota-box {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 8px 14px;
        font-size: 0.8rem;
        color: #aaa;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Elite Analytics - Dashboard Pro")

# ─── AVISO MUNDIAL 2026 ───────────────────
st.markdown("""
<div class="info-box">
🏆 <strong>¡El Mundial 2026 empezó hoy!</strong> — Selecciona 
<strong>soccer_fifa_world_cup</strong> en la liga para ver partidos en vivo.
Las ligas europeas (EPL, La Liga, etc.) están en temporada baja hasta agosto.
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONFIGURACIÓN — EN PÁGINA PRINCIPAL (mejor en móvil)
# ─────────────────────────────────────────
with st.expander("⚙️ Configuración — Claves API", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        api_gemini = st.text_input("🔑 Clave Gemini API:",
                                   type="password",
                                   help="https://aistudio.google.com/")
    with col2:
        api_odds = st.text_input("🔑 Clave Odds API:",
                                 type="password",
                                 help="https://the-odds-api.com/")

# ─────────────────────────────────────────
# LIGAS DISPONIBLES — con detección automática
# ─────────────────────────────────────────
LIGAS_CONOCIDAS = {
    "🌍 Mundial 2026 (ACTIVO AHORA)":          "soccer_fifa_world_cup",
    "🇺🇸 MLS - USA (ACTIVO)":                  "soccer_usa_mls",
    "🇧🇷 Copa Libertadores (ACTIVO)":           "soccer_conmebol_copa_libertadores",
    "🇬🇧 Premier League (temporada baja)":      "soccer_epl",
    "🇪🇸 La Liga (temporada baja)":             "soccer_spain_la_liga",
    "🇩🇪 Bundesliga (temporada baja)":          "soccer_germany_bundesliga",
    "🇮🇹 Serie A (temporada baja)":             "soccer_italy_serie_a",
    "🇫🇷 Ligue 1 (temporada baja)":             "soccer_france_ligue_one",
    "🏆 Champions League (temporada baja)":     "soccer_uefa_champs_league",
}

liga_label = st.selectbox(
    "🏆 Selecciona Liga:",
    list(LIGAS_CONOCIDAS.keys()),
    index=0,   # 👈 Mundial 2026 por defecto
)
liga = LIGAS_CONOCIDAS[liga_label]

# ─── Botón para detectar ligas con partidos activos ───
if api_odds:
    if st.button("🔍 Detectar ligas con partidos disponibles ahora"):
        with st.spinner("Consultando ligas activas..."):
            try:
                r = requests.get(
                    f"https://api.the-odds-api.com/v4/sports/?apiKey={api_odds}&all=false",
                    timeout=10
                ).json()
                if isinstance(r, list) and len(r) > 0:
                    futbol = [s for s in r if s.get("group", "").lower() == "soccer"
                              and s.get("has_outrights") is False]
                    if futbol:
                        st.success("✅ Ligas de fútbol con partidos activos:")
                        for s in futbol:
                            st.code(f"{s['title']}  →  key: {s['key']}")
                    else:
                        st.info("No se encontraron ligas de fútbol activas en este momento.")
                elif isinstance(r, dict) and r.get("message"):
                    st.error(f"Error Odds API: {r['message']}")
            except Exception as e:
                st.error(f"Error al consultar ligas: {e}")

st.markdown("---")

# ─────────────────────────────────────────
# CARGA DE PARTIDOS
# ─────────────────────────────────────────
partido = None
peticiones_restantes = None

if not api_odds:
    st.info("🔑 Ingresa tu clave de Odds API arriba para cargar partidos.")
else:
    url = (
        f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
        f"?apiKey={api_odds}&regions=eu&markets=h2h,totals"
    )
    try:
        r = requests.get(url, timeout=10)

        # Leer peticiones restantes del header
        peticiones_restantes = r.headers.get("x-requests-remaining", "?")

        resp = r.json()

        if isinstance(resp, dict) and resp.get("message"):
            st.error(f"❌ Error de Odds API: {resp['message']}")
        elif isinstance(resp, list) and len(resp) > 0:
            lista = {
                f"{p.get('home_team','Local')} vs {p.get('away_team','Visita')}": p
                for p in resp
            }
            partido_nombre = st.selectbox("🎯 Selecciona Partido:", list(lista.keys()))
            partido = lista[partido_nombre]
            st.markdown(
                f'<div class="quota-box">📊 Peticiones restantes en tu plan gratuito: '
                f'<strong>{peticiones_restantes}</strong> / 500 mensuales</div>',
                unsafe_allow_html=True
            )
        else:
            st.warning(
                f"⚠️ No hay partidos con cuotas disponibles para **{liga_label}** "
                f"en este momento. Prueba con **🌍 Mundial 2026** o **🇺🇸 MLS**."
            )

    except requests.exceptions.ConnectionError:
        st.error("❌ Sin conexión. Verifica tu internet.")
    except requests.exceptions.Timeout:
        st.error("❌ La petición tardó demasiado. Inténtalo de nuevo.")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")

contexto = st.text_area(
    "📋 Contexto adicional (lesiones, clima, rachas, bajas...):",
    placeholder="Ej: El delantero titular está lesionado. Lluvia prevista. El local lleva 5 victorias seguidas."
)

# ─────────────────────────────────────────
# BOTÓN DE ANÁLISIS
# ─────────────────────────────────────────
if st.button("🚀 Analizar 15 Mercados con Veracidad"):

    if not api_gemini:
        st.error("❌ Falta la clave de Gemini API.")
    elif not api_odds:
        st.error("❌ Falta la clave de Odds API.")
    elif not partido:
        st.error("❌ No hay partido seleccionado. Cambia la liga a **🌍 Mundial 2026**.")
    else:
        prompt = f"""
        ACTÚA COMO UN ANALISTA DE APUESTAS DEPORTIVAS EXPERTO Y ESTRICTO.

        Datos reales del partido obtenidos de la API:
        {partido}

        Contexto adicional:
        {contexto if contexto else "No se proporcionó contexto adicional."}

        INSTRUCCIÓN CRÍTICA: SI UN DATO NO EXISTE EN LA API, MARCA COMO 'DATO INSUFICIENTE'.
        ESTÁ COMPLETAMENTE PROHIBIDO INVENTAR CUOTAS, ESTADÍSTICAS O PROBABILIDADES.

        Genera análisis detallado para los siguientes 15 mercados:

        1. Ganador del partido (1X2)
        2. Doble Oportunidad
        3. Ambos Equipos Marcan (BTTS)
        4. Hándicap Asiático
        5. Resultado al Descanso (1X2)
        6. Resultado Descanso / Final
        7. Marcador Exacto (top 5 más probables)
        8. Primer Goleador
        9. Último Goleador
        10. Total Córners (Over/Under)
        11. Total Tarjetas (Over/Under)
        12. Equipo que Marca Primero
        13. Portería a Cero (Clean Sheet)
        14. Remates al Arco (Over/Under)
        15. TABLA DE GOLES — Over/Under: 0.5 / 1.5 / 2.5 / 3.5 / 4.5 / 5.5

        FORMATO OBLIGATORIO PARA CADA MERCADO:
        ### [Número]. [Nombre del Mercado]
        - **Selección recomendada:** [valor]
        - **Cuota de referencia:** [valor o 'DATO INSUFICIENTE']
        - **Confianza:** [Alta / Media / Baja]
        - **Justificación:** [Máximo 10 palabras basadas en datos reales]
        """

        with st.spinner("🔍 Procesando análisis con IA..."):
            try:
                client = genai.Client(api_key=api_gemini)
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=4096,
                        temperature=0.3,
                    )
                )
                respuesta = response.text

                st.markdown("---")
                st.markdown("### 🔥 Resultados del Análisis")

                for seccion in respuesta.split("###"):
                    if seccion.strip():
                        st.markdown(
                            f'<div class="card"><h3>{seccion.strip()}</h3></div>',
                            unsafe_allow_html=True
                        )

                st.success("✅ Análisis completado.")

            except Exception as e:
                st.error(f"❌ Error al generar el análisis: {e}")

# ─── Pie de página ────────────────────────
st.markdown("---")
st.caption("💡 Tier gratuito Odds API: 500 peticiones/mes · Gemini 3.5 Flash")
