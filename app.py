import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime
import math

# ═══════════════════════════════════════════════
# TRADUCCIONES Y BANDERAS
# ═══════════════════════════════════════════════
TRADUCCIONES = {
    "South Korea": "Corea del Sur", "Czech Republic": "República Checa",
    "Czechia": "República Checa", "Bosnia and Herzegovina": "Bosnia y Herz.",
    "Bosnia & Herzegovina": "Bosnia y Herz.", "Canada": "Canadá",
    "USA": "Estados Unidos", "United States": "Estados Unidos",
    "Switzerland": "Suiza", "Turkey": "Turquía", "Turkiye": "Turquía",
    "Germany": "Alemania", "Ivory Coast": "Costa de Marfil",
    "Brazil": "Brasil", "Morocco": "Marruecos", "Haiti": "Haití",
    "Scotland": "Escocia", "Spain": "España", "Cabo Verde": "Cabo Verde",
    "Saudi Arabia": "Arabia Saudita", "Croatia": "Croacia",
    "New Zealand": "Nueva Zelanda", "France": "Francia", "Japan": "Japón",
    "DR Congo": "RD Congo", "Congo DR": "RD Congo", "Uzbekistan": "Uzbekistán",
    "England": "Inglaterra", "Netherlands": "Países Bajos", "Belgium": "Bélgica",
    "Cameroon": "Camerún", "Peru": "Perú", "Iran": "Irán",
    "Denmark": "Dinamarca", "Poland": "Polonia", "Sweden": "Suecia",
    "Norway": "Noruega", "Ukraine": "Ucrania", "Wales": "Gales",
    "Algeria": "Argelia", "Egypt": "Egipto", "Tunisia": "Túnez",
    "Panama": "Panamá", "Jamaica": "Jamaica", "Iraq": "Irak",
    "Romania": "Rumania", "Hungary": "Hungría", "Slovakia": "Eslovaquia",
    "Slovenia": "Eslovenia", "Ireland": "Irlanda", "New Caledonia": "N. Caledonia"
}

BANDERAS = {
    "Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷", "Korea Republic":"🇰🇷",
    "Czechia":"🇨🇿","Czech Republic":"🇨🇿","USA":"🇺🇸",
    "United States":"🇺🇸","Paraguay":"🇵🇾","Canada":"🇨🇦",
    "Bosnia and Herzegovina":"🇧🇦", "Bosnia & Herzegovina":"🇧🇦", "Qatar":"🇶🇦",
    "Switzerland":"🇨🇭","Australia":"🇦🇺","Turkey":"🇹🇷","Turkiye":"🇹🇷",
    "Germany":"🇩🇪","Curacao":"🇨🇼","Ivory Coast":"🇨🇮","Ecuador":"🇪🇨",
    "Brazil":"🇧🇷","Morocco":"🇲🇦","Haiti":"🇭🇹","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Spain":"🇪🇸","Cabo Verde":"🇨🇻","Saudi Arabia":"🇸🇦","Argentina":"🇦🇷",
    "Croatia":"🇭🇷","New Zealand":"🇳🇿","Senegal":"🇸🇳","France":"🇫🇷",
    "Japan":"🇯🇵","Colombia":"🇨🇴","Portugal":"🇵🇹","DR Congo":"🇨🇩",
    "Congo DR":"🇨🇩","Uzbekistan":"🇺🇿","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Netherlands":"🇳🇱",
    "Belgium":"🇧🇪","Nigeria":"🇳🇬","Cameroon":"🇨🇲","Ghana":"🇬🇭",
    "Uruguay":"🇺🇾","Chile":"🇨🇱","Peru":"🇵🇪","Venezuela":"🇻🇪","Iran":"🇮🇷",
    "Serbia":"🇷🇸","Denmark":"🇩🇰","Poland":"🇵🇱","Sweden":"🇸🇪","Norway":"🇳🇴",
    "Ukraine":"🇺🇦","Wales":"🏴󠁧󠁢󠁷󠁬󠁳󠁿","Algeria":"🇩🇿","Egypt":"🇪🇬",
    "Tunisia":"🇹🇳","Costa Rica":"🇨🇷","Panama":"🇵🇦","Honduras":"🇭🇳",
    "Jamaica":"🇯🇲","UAE":"🇦🇪","Iraq":"🇮🇶","China":"🇨🇳","Indonesia":"🇮🇩",
    "Greece":"🇬🇷","Romania":"🇷🇴","Hungary":"🇭🇺","Slovakia":"🇸🇰",
    "Slovenia":"🇸🇮","Austria":"🇦🇹","Finland":"🇫🇮","Ireland":"🇮🇪","New Caledonia":"🇳🇨",
}

LIGAS = {
    "🌍 Mundial 2026 (ACTIVO)":          "soccer_fifa_world_cup",
    "🇺🇸 MLS (ACTIVO)":                   "soccer_usa_mls",
    "🇧🇷 Copa Libertadores (ACTIVO)":     "soccer_conmebol_copa_libertadores",
    "🇬🇧 Premier League":                  "soccer_epl",
    "🇪🇸 La Liga":                         "soccer_spain_la_liga",
    "🇩🇪 Bundesliga":                      "soccer_germany_bundesliga",
    "🇮🇹 Serie A":                         "soccer_italy_serie_a",
    "🇫🇷 Ligue 1":                         "soccer_france_ligue_one",
    "🏆 Champions League":                 "soccer_uefa_champs_league",
}

# ═══════════════════════════════════════════════
# FUNCIÓN CON CACHÉ PARA LA API DE ODDS
# ═══════════════════════════════════════════════
@st.cache_data(ttl=43200, show_spinner=False)
def obtener_partidos_api(liga, api_key):
    url = (f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
           f"?apiKey={api_key}&regions=eu&markets=h2h,totals")
    try:
        resp_raw = requests.get(url, timeout=10)
        restantes = resp_raw.headers.get("x-requests-remaining", "?")
        return resp_raw.json(), restantes
    except Exception as e:
        return {"message": str(e)}, "?"

# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def flag(team): return BANDERAS.get(team, "🏳️")

def extraer_odds(partido):
    home = partido.get("home_team","")
    away = partido.get("away_team","")
    h2h = {"home":None,"draw":None,"away":None}
    t_over, t_under = {}, {}
    for bk in partido.get("bookmakers",[]):
        for mkt in bk.get("markets",[]):
            if mkt["key"] == "h2h":
                for o in mkt["outcomes"]:
                    p = o["price"]
                    if o["name"] == home:
                        if h2h["home"] is None or p > h2h["home"]: h2h["home"] = round(p,2)
                    elif o["name"] == away:
                        if h2h["away"] is None or p > h2h["away"]: h2h["away"] = round(p,2)
                    elif o["name"] == "Draw":
                        if h2h["draw"] is None or p > h2h["draw"]: h2h["draw"] = round(p,2)
            elif mkt["key"] == "totals":
                for o in mkt["outcomes"]:
                    pt = o.get("point", 2.5); p = o["price"]
                    if o["name"] == "Over":
                        if pt not in t_over or p > t_over[pt]: t_over[pt] = round(p,2)
                    else:
                        if pt not in t_under or p > t_under[pt]: t_under[pt] = round(p,2)
    return h2h, t_over, t_under

def calcular_probs(h2h):
    if not all(v is not None for v in h2h.values()):
        return {"home":40,"draw":30,"away":30}
    ph, pd, pa = 1/h2h["home"], 1/h2h["draw"], 1/h2h["away"]
    total = ph + pd + pa
    home_p = round(ph/total*100)
    draw_p = round(pd/total*100)
    away_p = 100 - home_p - draw_p
    return {"home": home_p, "draw": draw_p, "away": away_p}

def mejor_apuesta(h2h, probs, t_over, t_under, home_es, away_es):
    cands = []
    for pt in sorted(t_over.keys()):
        if pt in t_under:
            total = (1/t_over[pt]) + (1/t_under[pt])
            cands.append({"label": f"Más de {pt} Goles",  "odds": t_over[pt],  "prob": round((1/t_over[pt])/total*100)})
            cands.append({"label": f"Menos de {pt} Goles","odds": t_under[pt], "prob": round((1/t_under[pt])/total*100)})
    
    if h2h["home"]: cands.append({"label":f"Gana {home_es}","odds":h2h["home"],"prob":probs["home"]})
    if h2h["draw"]: cands.append({"label":"Empate","odds":h2h["draw"],"prob":probs["draw"]})
    if h2h["away"]: cands.append({"label":f"Gana {away_es}","odds":h2h["away"],"prob":probs["away"]})
    
    return max(cands, key=lambda x: x["prob"]) if cands else None

def fmt_fecha(iso, simple=False):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        if simple: return dt.strftime('%Y-%m-%d')
        dias = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt.isoweekday()%7]} {dt.day} {meses[dt.month]} · {dt.strftime('%H:%M')} UTC"
    except: return "Fecha no disponible"

def render_simplified_card(partido, idx=1):
    home_en = partido.get("home_team","Local")
    away_en = partido.get("away_team","Visita")
    
    # Traducciones al Español
    home_es = TRADUCCIONES.get(home_en, home_en)
    away_es = TRADUCCIONES.get(away_en, away_en)
    
    fecha = fmt_fecha(partido.get("commence_time",""))
    h2h, t_over, t_under = extraer_odds(partido)
    probs = calcular_probs(h2h)
    best = mejor_apuesta(h2h, probs, t_over, t_under, home_es, away_es)
    
    hp, dp, ap = probs["home"], probs["draw"], probs["away"]
    
    # Formateo de Cuotas (Odds) para la UI
    odd_h = f"@{h2h['home']}" if h2h.get('home') else "N/A"
    odd_d = f"@{h2h['draw']}" if h2h.get('draw') else "N/A"
    odd_a = f"@{h2h['away']}" if h2h.get('away') else "N/A"

    # HTML para la Mejor Apuesta recomendada
    best_bet_html = ""
    if best:
        best_bet_html = f"""
        <div style="background:#00e67615; color:#00e676; border:1px solid #00e67640; 
                    padding:6px; border-radius:8px; font-size:12px; font-weight:700; 
                    text-align:center; margin-top:12px; letter-spacing:0.3px;">
            🔥 Destacada: {best['label']} ({best['odds']})
        </div>
        """

    return f"""
<div style="background:#161c2b;border-radius:12px;padding:14px;border:1px solid #2a3349;
            margin-bottom:14px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <span style="color:#8b949e;font-size:12px;font-weight:600;">📅 {fecha}</span>
    <span style="background:#2d3748;color:#e1e1e1;font-size:10px;padding:3px 8px;border-radius:20px;font-weight:800;">M {idx}</span>
  </div>

  <div style="display:flex;align-items:center;margin-bottom:14px;">
    <div style="flex:1;text-align:center;">
      <div style="font-size:36px;line-height:1.1;margin-bottom:4px;">{flag(home_en)}</div>
      <div style="color:#e1e1e1;font-weight:700;font-size:13px;">{home_es}</div>
      <div style="color:#00e676;font-size:12px;font-weight:800;margin-top:2px;">{odd_h}</div>
    </div>
    
    <div style="flex:1;text-align:center;">
      <div style="color:#6b7280;font-size:13px;font-weight:900;letter-spacing:1px;margin-bottom:2px;">VS</div>
      <div style="color:#8b949e;font-size:10px;font-weight:600;">EMP</div>
      <div style="color:#e1e1e1;font-size:12px;font-weight:700;">{odd_d}</div>
    </div>
    
    <div style="flex:1;text-align:center;">
      <div style="font-size:36px;line-height:1.1;margin-bottom:4px;">{flag(away_en)}</div>
      <div style="color:#e1e1e1;font-weight:700;font-size:13px;">{away_es}</div>
      <div style="color:#00e676;font-size:12px;font-weight:800;margin-top:2px;">{odd_a}</div>
    </div>
  </div>

  <div style="display:flex;border-radius:8px;overflow:hidden;height:22px;box-shadow:inset 0 1px 3px rgba(0,0,0,0.3);">
    <div style="background:#22c55e;width:{hp}%;display:flex;align-items:center;
                justify-content:center;color:white;font-size:11px;font-weight:800;min-width:24px;">{hp}%</div>
    <div style="background:#4b5563;width:{dp}%;display:flex;align-items:center;
                justify-content:center;color:#e1e1e1;font-size:10px;font-weight:600;min-width:24px;">{dp}%</div>
    <div style="background:#ef4444;width:{ap}%;display:flex;align-items:center;
                justify-content:center;color:white;font-size:11px;font-weight:800;min-width:24px;">{ap}%</div>
  </div>
  
  {best_bet_html}
</div>"""

# ═══════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡COMBINADAS", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  [data-testid="stAppViewContainer"]  { background:#0d1117 !important; }
  [data-testid="stHeader"]            { background:transparent !important; }
  [data-testid="stDecoration"]        { display:none; }
  [data-testid="stToolbar"]           { display:none; }
  section[data-testid="stSidebar"]    { display:none; }
  .block-container { padding-top:0.8rem !important; max-width:520px !important; }

  label, .stTextInput label, .stTextArea label,
  .stSelectbox label { color:#8b949e !important; font-size:12px !important; font-weight:600 !important; }
  .stTextInput input, .stTextArea textarea {
    background:#161c2b !important; color:#e1e1e1 !important;
    border:1px solid #2d3748 !important; border-radius:10px !important; font-size:13px !important;
  }
  [data-testid="stSelectbox"] > div > div {
    background:#161c2b !important; border:1px solid #2d3748 !important;
    border-radius:10px !important; color:#e1e1e1 !important;
  }
  [data-testid="stExpander"] {
    background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:12px !important;
  }
  [data-testid="stExpanderToggleIcon"] svg { fill:#00e676 !important; }

  .stButton > button {
    background:linear-gradient(90deg,#00e676,#00b4d8) !important;
    border:none !important; border-radius:12px !important;
    color:#0d1117 !important; font-weight:800 !important;
    font-size:14px !important; width:100% !important; padding:0.65em !important;
  }
  .stButton > button:hover { opacity:.9; }
  
  .btn-actualizar > button {
    background:#2d3748 !important; color:#e1e1e1 !important;
    font-size:12px !important; margin-top: 28px !important;
  }

  [data-testid="stAlert"] { border-radius:12px !important; }
  hr { border-color:#2d3748 !important; }

  .result-card {
    background:#161c2b; border-left:4px solid #00e676; border-radius:12px; padding:16px; margin-bottom:14px;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    color:#e1e1e1; font-size:13px; line-height:1.6;
  }
</style>
""", unsafe_allow_html=True)

# ─── HEADER Y CLAVES ─────────────────────────────────────────────
api_gemini_ss = st.session_state.get("_gem","")
api_odds_ss   = st.session_state.get("_odd","")
online = bool(api_gemini_ss and api_odds_ss)
dot    = "🟢" if online else "🔴"
badge  = "EN LÍNEA" if online else "SIN CONEXIÓN"
bcol   = "#22c55e" if online else "#ef4444"

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            background:#161c2b;padding:13px 16px;border-radius:14px;
            margin-bottom:16px;border:1px solid #2d3748;">
  <span style="font-size:20px;font-weight:900;color:#e1e1e1;letter-spacing:.5px;">
    BET<span style="color:#00e676;">⚡</span>COMBINADAS
  </span>
  <span style="border:1px solid {bcol};color:{bcol};font-size:10px;font-weight:700;
               padding:4px 10px;border-radius:20px;letter-spacing:.5px;">{dot} {badge}</span>
</div>
""", unsafe_allow_html=True)

# ─── CONFIGURACIÓN ───────────────────────────────────────────────
with st.expander("⚙️ Configuración — Claves API", expanded=not online):
    c1, c2 = st.columns(2)
    with c1:
        api_gemini = st.text_input("Gemini API Key", type="password", help="aistudio.google.com", key="_gem")
    with c2:
        api_odds = st.text_input("Odds API Key", type="password", help="the-odds-api.com", key="_odd")

# ─── SELECCIÓN DE LIGA Y BOTÓN ACTUALIZAR ────────────────────────
col_liga, col_btn = st.columns([3, 1])

with col_liga:
    liga_label = st.selectbox("🏆 Liga para analizar", list(LIGAS.keys()), index=0)
    liga = LIGAS[liga_label]

with col_btn:
    st.markdown('<div class="btn-actualizar">', unsafe_allow_html=True)
    if st.button("🔄 Actualizar", help="Forzar descarga desde la API (gasta 1 petición)"):
        if api_odds:
            obtener_partidos_api.clear(liga, api_odds)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─── LÓGICA DE CARGA (Usando Caché) ──────────────────────────────
upcoming_matches = []
upcoming_matches_dict = {}
restantes = "?"

if api_odds:
    with st.spinner("🚀 Consultando cuotas..."):
        resp, restantes = obtener_partidos_api(liga, api_odds)
        
        if isinstance(resp, list) and len(resp) > 0:
            sorted_resp = sorted(resp, key=lambda x: x.get('commence_time', ''))
            upcoming_matches = sorted_resp[:6]
            for p in upcoming_matches:
                home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
                away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
                name = f"{fmt_fecha(p['commence_time'], simple=True)}: {home_es} vs {away_es}"
                upcoming_matches_dict[name] = p
        elif isinstance(resp, dict) and resp.get("message"):
             st.error(f"❌ Odds API Error: {resp['message']}")
        else:
             st.warning("⚠️ No se encontraron próximos partidos para esta liga.")

st.markdown("---")

# ─── SELECCIÓN DE PARTIDOS ─────────────────────────────────────
st.subheader("🎯 Selecciona de los próximos 6 partidos")

if upcoming_matches_dict:
    selected_match_names = st.multiselect(
        "Selecciona hasta 6 partidos",
        options=list(upcoming_matches_dict.keys()),
        default=None
    )
    
    selected_matches = [upcoming_matches_dict[name] for name in selected_match_names]

    if selected_matches:
        st.markdown("### 📊 Análisis del Mercado")
        for i, p in enumerate(selected_matches):
            st.markdown(render_simplified_card(p, i+1), unsafe_allow_html=True)
            
        st.markdown(
            f'<div style="color:#6b7280;font-size:10px;text-align:right;'
            f'margin-top:-8px;margin-bottom:10px;">'
            f'⚡ Peticiones restantes: <strong style="color:#e1e1e1;">{restantes}</strong>/500</div>',
            unsafe_allow_html=True
        )
else:
    selected_matches = []
    st.info("Ingresa tus claves API arriba para ver los próximos partidos disponibles.")

# ─── CONTEXTO + ANÁLISIS IA ────────────────────────────────────
st.markdown("---")
contexto = st.text_area(
    "📋 Contexto adicional para la IA (opcional)",
    placeholder="Ej: El local necesita ganar para clasificar, el árbitro saca muchas tarjetas..."
)

if st.button("🚀 Generar Estrategias (Segura/Media/Arriesgada)"):
    if not api_gemini:
        st.error("❌ Falta la Gemini API Key. Ponla en Configuración.")
    elif not selected_matches:
        st.error("❌ Selecciona al menos un partido primero.")
    else:
        formatted_matches = []
        for p in selected_matches:
            h2h, t_over, t_under = extraer_odds(p)
            probs = calcular_probs(h2h)
            home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
            away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
            best = mejor_apuesta(h2h, probs, t_over, t_under, home_es, away_es)
            
            p_data = {
                "local": home_es,
                "visita": away_es,
                "fecha": fmt_fecha(p['commence_time'], simple=True),
                "probabilidades": probs,
                "mejor_apuesta_individual": best,
                "cuotas_1x2": h2h,
                "goles_over": t_over,
                "goles_under": t_under
            }
            formatted_matches.append(p_data)

        prompt = f"""
Actúa como un tipster y analista experto en apuestas deportivas de fútbol. Tu tarea es analizar los siguientes partidos seleccionados y generar tres opciones de apuestas (parleys/combinadas) categorizadas por nivel de riesgo.

Datos de los partidos en formato JSON (cuotas reales extraídas de mercados 1X2 y Totales Over/Under de las casas de apuestas, junto con las probabilidades matemáticas):
{formatted_matches}

Contexto adicional del usuario: {contexto or 'Sin contexto adicional proporcionado.'}

INSTRUCCIONES:
Elige el mejor partido (o combina los mejores de la lista) para construir tus pronósticos. Usa las cuotas proporcionadas como base fundamental. Para las predicciones tácticas (córners, tarjetas, tiros), usa tu base de datos de conocimiento sobre cómo juegan estos equipos.

Antes de dar los pronósticos, haz una muy breve introducción (dos o tres líneas) sobre el contexto táctico de los partidos seleccionados basándote en los datos y tu conocimiento.

Luego, entrégame las tres apuestas siguiendo ESTRICTAMENTE esta estructura y formato, utilizando encabezados "##":

## 1. La Apuesta Segura (Bajo Riesgo)
* **Formato:** Una apuesta combinada clásica de máximo 2 selecciones. Prioriza que ambas selecciones sean de un MISMO partido de la lista.
* **Requisito:** Deben ser los mercados más probables basándote en el JSON (ej. Doble Oportunidad, Más/Menos goles). Justifica brevemente por qué es segura basándote en la tendencia y las probabilidades provistas.

## 2. La Apuesta Moderada (Riesgo Medio)
* **Formato:** Una función "Crear Apuesta" (Bet Builder) de 3 a 4 selecciones para UN MISMO PARTIDO de la lista.
* **Requisito:** Incluye los mercados de goles/resultado del JSON y combínalos con tus propias inferencias tácticas (ej. tiros a puerta de un jugador clave, más de X córners o tarjetas). Justifica cada selección con datos tácticos o el estilo de juego real de los equipos.

## 3. La Apuesta Arriesgada (Baja Inversión, Cuota Alta)
* **Formato:** Un parley largo de 5 a 7 selecciones. Puedes usar un "Crear Apuesta" de un solo partido o mezclar varios de la lista.
* **Requisito:** Aunque es arriesgada por la cantidad de líneas, CADA SELECCIÓN debe tener una alta probabilidad matemática o táctica de ocurrir. Utiliza líneas bajas de córners, faltas, o mercados del JSON. Justifica cada punto de forma rápida y directa.

Tono y Estilo:
El lenguaje debe ser profesional, objetivo y persuasivo. No uses lenguaje excesivamente complejo.
"""
        with st.spinner("🧠 Procesando datos matemáticos y tácticos..."):
            try:
                client = genai.Client(api_key=api_gemini)
                resp = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.2)
                )
                texto = resp.text
                st.markdown("### 🔥 El Veredicto de la IA")
                
                for sec in texto.split("##"):
                    if sec.strip():
                        lines = sec.strip().split('\n')
                        title = lines[0].strip()
                        content = '\n'.join(lines[1:]).strip()
                        
                        st.markdown(
                            f'<div class="result-card">'
                            f'<h3 style="color:#00e676;margin-top:0;">{title}</h3>'
                            f'{content}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                st.success("✅ Análisis completado con éxito.")
            except Exception as e:
                st.error(f"❌ Error al consultar IA: {e}")

st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
