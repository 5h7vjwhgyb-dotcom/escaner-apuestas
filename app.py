import streamlit as st
import requests
import google.generativeai as genai

# --- DISEÑO ---
st.set_page_config(page_title="Analytics Pro", layout="wide")
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    .card { background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(10px); 
            padding: 20px; border-radius: 20px; border-left: 5px solid #00ff9d; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Elite Sports Analytics")

with st.sidebar:
    api_gemini = st.text_input("Clave Gemini:", type="password")
    api_odds = st.text_input("Clave Odds API:", type="password")

if api_odds:
    # URL con mercados extendidos para tus 15 categorías
    url = f'https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_odds}&regions=eu&markets=h2h,totals,corners'
    resp = requests.get(url).json()
    lista = {f"{p['home_team']} vs {p['away_team']}": p for p in resp}
    partido_nombre = st.selectbox("Partido:", list(lista.keys()))
    partido = lista[partido_nombre]
else:
    st.info("Ingresa claves en el menú lateral.")
    partido = None
contexto = st.text_area("Contexto cualitativo:")

if st.button("🚀 Analizar 15 Mercados"):
    if api_gemini and partido:
        genai.configure(api_key=api_gemini)
        modelo = genai.GenerativeModel('gemini-3.5-flash')
        prompt = f"""Analiza {partido}. Contexto: {contexto}.
        Genera 15 mercados: 1. Ganador, 2. Doble O, 3. Ambos Marcan, 4. Hándicap, 5. Descanso, 6. Descanso/Final, 7. Marcador, 8. 1er Goleador, 9. Último Goleador, 10. Córners, 11. Tarjetas, 12. Gol primero, 13. Portería a cero, 14. Remates, 15. Goles (Tabla 0.5 a 5.5).
        Formato: ### [Mercado] \n - [Pick] @ [Cuota] | Confianza: [Alta/Media/Baja] | Justificación: [Breve]."""
        
        with st.spinner('Analizando...'):
            res = modelo.generate_content(prompt).text
            for s in res.split("###"):
                if s.strip(): st.markdown(f'<div class="card">{s}</div>', unsafe_allow_html=True)
