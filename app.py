import streamlit as st
import requests
import google.generativeai as genai

# --- DISEÑO Y CONFIGURACIÓN ---
st.set_page_config(page_title="Analytics Pro", layout="wide")
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    .card { background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(12px); 
            padding: 20px; border-radius: 20px; border-left: 6px solid #00ff9d; margin-bottom: 20px; 
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); }
    h3 { color: #00ff9d !important; font-size: 1.2rem; }
    .stButton > button { background: linear-gradient(90deg, #00ff9d, #00d2ff); 
                         border: none; border-radius: 12px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Elite Analytics - Dashboard Pro")

# --- LÓGICA DE API SEGURA ---
with st.sidebar:
    st.header("⚙️ Configuración")
    api_gemini = st.text_input("Clave Gemini:", type="password")
    api_odds = st.text_input("Clave Odds API:", type="password")

partido = None
if api_odds:
    url = f'https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_odds}&regions=eu&markets=h2h,totals,corners'
    try:
        resp = requests.get(url, timeout=10).json()
        if isinstance(resp, list) and len(resp) > 0:
            lista = {f"{p.get('home_team', 'Local')} vs {p.get('away_team', 'Visita')}": p for p in resp}
            partido_nombre = st.selectbox("Selecciona Partido:", list(lista.keys()))
            partido = lista[partido_nombre]
        else:
            st.warning("No hay partidos disponibles.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

contexto = st.text_area("Contexto (lesiones, clima, rachas...):")

# --- ANÁLISIS INTEGRAL 15 MERCADOS ---
if st.button("🚀 Analizar 15 Mercados con Veracidad"):
    if api_gemini and partido:
        genai.configure(api_key=api_gemini)
        modelo = genai.GenerativeModel('gemini-3.5-flash')
        
        prompt = f"""
        ACTÚA COMO UN ANALISTA DE DATOS ESTRICTO.
        Datos reales del partido: {partido}. Contexto: {contexto}.
        
        Genera predicciones detalladas para los siguientes 15 mercados. 
        SI UN DATO NO EXISTE EN LA API, MARCA COMO 'DATO INSUFICIENTE'. PROHIBIDO INVENTAR.
        
        Mercados:
        1. Ganador (1X2), 2. Doble Oportunidad, 3. Ambos Marcan, 
        4. Hándicap Asiático, 5. Resultado al descanso, 6. Resultado descanso/final, 
        7. Marcador exacto, 8. Primer goleador, 9. Último goleador, 
        10. Total córners, 11. Total tarjetas, 12. Gol primero, 
        13. Portería a cero, 14. Remates al arco.
        15. TABLA DE GOLES (PROBABILIDAD): Over/Under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5.

        FORMATO OBLIGATORIO:
        ### [Nombre del Mercado]
        - [Selección] @ [Cuota] | Confianza: [Alta/Media/Baja] | Justificación: [Máx 5 palabras].
        """
        
        with st.spinner('Procesando dashboard...'):
            try:
                respuesta = modelo.generate_content(prompt).text
                st.markdown("### 🔥 Resultados del Análisis")
                for seccion in respuesta.split("###"):
                    if seccion.strip():
                        st.markdown(f'<div class="card">{seccion}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error("Error al procesar el análisis. Intenta nuevamente.")
