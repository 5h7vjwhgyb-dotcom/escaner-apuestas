import streamlit as st
import requests
import google.generativeai as genai

# 1. Configuración de la página web
st.set_page_config(page_title="Analytics Scanner", page_icon="⚽", layout="centered")
st.title("📊 Escáner Analítico de Apuestas")

# 2. Menú lateral para las configuraciones y seguridad
with st.sidebar:
    st.header("⚙️ Configuración del Sistema")
    st.write("Ingresa tus credenciales para habilitar el motor:")
    api_gemini = st.text_input("Clave de Google AI Studio:", type="password")
    api_odds = st.text_input("Clave de The Odds API:", type="password")
    
    st.divider()
    st.write("Selecciona la liga a escanear:")
    torneo = st.selectbox("Liga / Torneo", [
        "soccer_fifa_world_cup", 
        "soccer_epl", 
        "soccer_mexico_ligamx", 
        "basketball_nba"
    ])

# 3. Interfaz principal para el usuario
st.write("### Contexto del Partido")
st.write("Ingresa las variables cualitativas para que la IA ajuste la probabilidad matemática.")
contexto_usuario = st.text_area(
    "Lesiones, clima, localía, rachas, altitud, etc.:", 
    placeholder="Ej: El equipo local juega con suplentes y hay alerta de lluvia..."
)

# 4. El Botón de Acción
if st.button("🚀 Iniciar Escáner y Analizar", use_container_width=True):
    
    # Validar que las llaves estén ingresadas
    if not api_gemini or not api_odds:
        st.warning("⚠️ Por favor ingresa ambas claves API en el menú lateral de la izquierda.")
    else:
        # Configurar el cerebro (IA)
        genai.configure(api_key=api_gemini)
        instrucciones = """
        Eres un algoritmo avanzado de Sports Analytics especializado en la detección de "Apuestas de Valor".
        Ejecuta este proceso:
        1. CÁLCULO DE PROBABILIDAD IMPLÍCITA: Calcula la probabilidad exigida usando: (1 / cuota) * 100. Obligatorio: Debes incluir los pasos de desarrollo detallados de la fórmula matemática.
        2. AJUSTE DE CONTEXTO: Evalúa las variables entregadas por el usuario.
        3. PROBABILIDAD REAL: Asigna un porcentaje de éxito real.
        4. VEREDICTO DE VALOR: 
        - Si Probabilidad Real > Probabilidad Implícita = "VEREDICTO: VALOR POSITIVO".
        - Si es menor o igual = "VEREDICTO: SIN VALOR".
        """
        
        modelo = genai.GenerativeModel(
            model_name='gemini-3.5-flash', 
            system_instruction=instrucciones,
            generation_config={"temperature": 0.0}
        )
        
        # Conectar con las casas de apuestas
        url = f'https://api.the-odds-api.com/v4/sports/{torneo}/odds/?apiKey={api_odds}&regions=eu&markets=h2h'
        
        with st.spinner('📡 Escaneando el mercado mundial de cuotas...'):
            resp = requests.get(url)
            
        if resp.status_code == 200:
            datos = resp.json()
            if len(datos) > 0:
                partido = datos[0]
                equipo_local = partido['home_team']
                equipo_visitante = partido['away_team']
                
                # Algoritmo de búsqueda de la mejor cuota
                mejor_cuota = 0.0
                casa = ""
                for bookmaker in partido['bookmakers']:
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == equipo_local and outcome['price'] > mejor_cuota:
                                    mejor_cuota = outcome['price']
                                    casa = bookmaker['title']
                                    
                st.success(f"✅ Mejor mercado encontrado: **{equipo_local}** a cuota **{mejor_cuota}** en {casa}")
                
                # Compilar datos y enviar a la IA
                prompt_final = f"""
                Partido: {equipo_local} vs {equipo_visitante}
                Cuota para {equipo_local}: {mejor_cuota}
                Contexto cualitativo: {contexto_usuario}
                """
                
                with st.spinner('🧠 Ejecutando matemática y análisis de valor...'):
                    try:
                        respuesta = modelo.generate_content(prompt_final)
                        st.markdown(respuesta.text)
                    except Exception as e:
                        st.error(f"⚠️ Error de procesamiento IA: {e}")
            else:
                st.info("No hay partidos próximos programados para la liga seleccionada.")
        else:
            st.error("⚠️ Error de conexión con The Odds API. Verifica tu clave.")
