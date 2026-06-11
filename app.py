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
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        background: rgba(255,255,255,0.07) !important;
        color: white !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Elite Analytics - Dashboard Pro")

# ─────────────────────────────────────────
# PANEL LATERAL — CONFIGURACIÓN
# ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")

    api_gemini = st.text_input("🔑 Clave Gemini API:", type="password",
                               help="Obtén tu clave en https://aistudio.google.com/")

    api_odds = st.text_input("🔑 Clave Odds API:", type="password",
                             help="Obtén tu clave en https://the-odds-api.com/")

    liga = st.selectbox("🏆 Liga:", [
        "soccer_epl",
        "soccer_spain_la_liga",
        "soccer_germany_bundesliga",
        "soccer_italy_serie_a",
        "soccer_france_ligue_one",
        "soccer_usa_mls",
        "soccer_uefa_champs_league",
        "soccer_conmebol_copa_libertadores",
        "soccer_fifa_world_cup",
    ])

    st.markdown("---")
    st.caption("💡 Tier gratuito de Odds API: 500 peticiones/mes")

# ─────────────────────────────────────────
# CARGA DE PARTIDOS
# ─────────────────────────────────────────
partido = None

if not api_odds:
    st.info("🔑 Ingresa tu clave de Odds API en el panel lateral para cargar partidos.")
else:
    # FIX: Se eliminó 'corners' — no disponible en el tier gratuito de Odds API
    url = (
        f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
        f"?apiKey={api_odds}&regions=eu&markets=h2h,totals"
    )
    try:
        resp = requests.get(url, timeout=10).json()

        # FIX: Detectar y mostrar errores reales de la API
        if isinstance(resp, dict) and resp.get("message"):
            st.error(f"❌ Error de Odds API: {resp['message']}")
        elif isinstance(resp, list) and len(resp) > 0:
            lista = {
                f"{p.get('home_team', 'Local')} vs {p.get('away_team', 'Visita')}": p
                for p in resp
            }
            partido_nombre = st.selectbox("🎯 Selecciona Partido:", list(lista.keys()))
            partido = lista[partido_nombre]
        else:
            st.warning("⚠️ No hay partidos disponibles para esta liga ahora mismo.")

    except requests.exceptions.ConnectionError:
        st.error("❌ Sin conexión. Verifica tu internet e inténtalo de nuevo.")
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

    # FIX: Validación clara antes de proceder
    if not api_gemini:
        st.error("❌ Falta la clave de Gemini API. Agrégala en el panel lateral.")
    elif not api_odds:
        st.error("❌ Falta la clave de Odds API. Agrégala en el panel lateral.")
    elif not partido:
        st.error("❌ No hay partido seleccionado. Verifica tu clave de Odds API y la liga elegida.")
    else:
        prompt = f"""
        ACTÚA COMO UN ANALISTA DE APUESTAS DEPORTIVAS EXPERTO Y ESTRICTO.

        Datos reales del partido obtenidos de la API:
        {partido}

        Contexto adicional proporcionado por el usuario:
        {contexto if contexto else "No se proporcionó contexto adicional."}

        INSTRUCCIÓN CRÍTICA: SI UN DATO NO EXISTE EN LA API, MARCA COMO 'DATO INSUFICIENTE'.
        ESTÁ COMPLETAMENTE PROHIBIDO INVENTAR CUOTAS, ESTADÍSTICAS O PROBABILIDADES.

        Genera un análisis detallado para los siguientes 15 mercados:

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
                # FIX: Nueva SDK google-genai compatible con gemini-3.5-flash
                client = genai.Client(api_key=api_gemini)
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=4096,
                        temperature=0.3,   # Baja temperatura = respuestas más precisas
                    )
                )
                respuesta = response.text

                st.markdown("---")
                st.markdown("### 🔥 Resultados del Análisis")

                for seccion in respuesta.split("###"):
                    if seccion.strip():
                        st.markdown(
                            f'<div class="card"><h3>### {seccion.strip()}</h3></div>',
                            unsafe_allow_html=True
                        )

                st.success("✅ Análisis completado.")

            # FIX: Errores específicos y visibles
            except genai.errors.APIError as e:
                st.error(f"❌ Error de Gemini API: {e}")
            except Exception as e:
                st.error(f"❌ Error al generar el análisis: {e}")
