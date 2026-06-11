import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

# --- DISEÑO GLASSMORPHISM ---
st.set_page_config(page_title="Analytics Pro", layout="wide")
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    div.stButton > button { background: linear-gradient(90deg, #ff9a9e, #fad0c4); border-radius: 15px; font-weight: bold; }
    .glass { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px); border-radius: 20px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Elite Sports Analytics - Veracidad Total")

# --- LÓGICA DE API ---
with st.sidebar:
    api_gemini = st.text_input("Clave Gemini:", type="password")
    api_odds = st.text_input("Clave Odds API:", type="password")

if api_odds:
    # Filtramos partidos de los próximos 3 días
    url = f'https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_odds}&regions=eu&markets=h2h'
    resp = requests.get(url).json()
    
    # Filtro lógico para 3 días (72 horas)
    ahora = datetime.utcnow()
    limite = ahora + timedelta(days=3)
    partidos_filtrados = []
    
    for p in resp:
        # Convertimos fecha ISO a objeto datetime
        commence = datetime.strptime(p['commence_time'], '%Y-%m-%dT%H:%M:%SZ')
        if commence <= limite:
            partidos_filtrados.append(p)
            
    lista_nombres = {f"{p['commence_time']} | {p['home_team']} vs {p['away_team']}": p for p in partidos_filtrados}
    partido = st.selectbox("Próximos partidos (3 días):", list(lista_nombres.keys()))
    partido_seleccionado = lista_nombres[partido]
else:
    st.info("Ingresa tu clave de Odds API.")
    partido_seleccionado = None

# --- ANÁLISIS ---
if st.button("🚀 Analizar con Datos Verídicos"):
    if api_gemini and partido_seleccionado:
        genai.configure(api_key=api_gemini)
        modelo = genai.GenerativeModel('gemini-3.5-flash')
        
        # INSTRUCCIONES DE ORO: Cero invención
        prompt = f"""
        ACTÚA COMO UN ANALISTA DE DATOS ESTRICTO.
        Datos reales del partido: {partido_seleccionado}.
        REGLAS:
        1. NO ALUCINES. Si no tienes la estadística de una lesión o clima, NO LA INVENTES.
        2. BASA TODO EN LAS CUOTAS REALES PROPORCIONADAS.
        3. Si la información es insuficiente, decláralo.
        4. Genera obligatoriamente 3 secciones: ### Segura, ### Media, ### Arriesgada.
        """
        
        with st.spinner('Analizando datos reales...'):
            respuesta = modelo.generate_content(prompt).text
            st.markdown(respuesta)
