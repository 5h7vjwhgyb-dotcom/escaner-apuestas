import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime
import math
import json

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
        # Retorna ej: "Sáb 13 Jun · 19:00 UTC"
        return f"{dias[dt.isoweekday()%7]} {dt.day} {meses[dt.month]} · {dt.strftime('%H:%M')} UTC"
    except: return "Fecha no disponible · 00:00 UTC"

def render_simplified_card(partido, idx=1):
    home_en = partido.get("home_team","Local")
    away_en = partido.get("away_team","Visita")
    
    home_es = TRADUCCIONES.get(home_en, home_en)
    away_es = TRADUCCIONES.get(away_en, away_en)
    
    fecha = fmt_fecha(partido.get("commence_time",""))
    h2h, t_over, t_under = extraer_odds(partido)
    probs = calcular_probs(h2h)
    best = mejor_apuesta(h2h, probs, t_over, t_under, home_es, away_es)
    
    hp, dp, ap = probs["home"], probs["draw"], probs["away"]
    
    odd_h = f"@{h2h['home']}" if h2h.get('home') else "N/A"
    odd_d = f"@{h2h['draw']}" if h2h.get('draw') else "N/A"
    odd_a = f"@{h2h['away']}" if h2h.get('away') else "N/A"

    best_bet_html = ""
    if best:
        best_bet_html = f"""<div style="background:#00e67615; color:#00e676; border:1px solid #00e67640; padding:6px; border-radius:8px; font-size:12px; font-weight:700; text-align:center; margin-top:12px; letter-spacing:0.3px;">💡 Valor Matemático: {best['label']} ({best['odds']})</div>"""

    return f"""<div style="background:#161c2b;border-radius:12px;padding:14px;border:1px solid #2a3349;margin-bottom:14px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
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
<div style="background:#22c55e;width:{hp}%;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:800;min-width:24px;">{hp}%</div>
<div style="background:#4b5563;width:{dp}%;display:flex;align-items:center;justify-content:center;color:#e1e1e1;font-size:10px;font-weight:600;min-width:24px;">{dp}%</div>
<div style="background:#ef4444;width:{ap}%;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:800;min-width:24px;">{ap}%</div>
</div>
{best_bet_html}
</div>"""

# ═══════════════════════════════════════════════════════════════
# APP UI
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

  label, .stTextInput label, .stTextArea label { 
      color:#8b949e !important; font-size:12px !important; font-weight:600 !important; 
  }
  .stTextInput input, .stTextArea textarea {
    background:#161c2b !important; color:#e1e1e1 !important;
    border:1px solid #2d3748 !important; border-radius:10px !important; font-size:13px !important;
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
    font-size:12px !important; margin-top: 25px !important;
  }

  [data-testid="stAlert"] { border-radius:12px !important; }
  hr { border-color:#2d3748 !important; }
  
  /* PESTAÑAS TABS INFERIORES */
  [data-testid="stTabs"] button {
    background-color: #161c2b !important; color: #8b949e !important;
    font-weight: 700 !important; border-radius: 8px !important;
    border: 1px solid #2d3748 !important; padding: 6px 16px !important; margin-right: 8px !important;
  }
  [data-testid="stTabs"] button[aria-selected="true"] {
    background-color: #00e67615 !important; color: #00e676 !important;
    border: 1px solid #00e676 !important; box-shadow: 0 0 10px rgba(0,230,118,0.1) !important;
  }
  
  /* MAGIA CSS: CONVERTIR RADIO BUTTONS EN "PÍLDORAS" PARA LAS LIGAS */
  div[role="radiogroup"] {
      gap: 8px; flex-wrap: wrap; margin-bottom: 10px;
  }
  div[role="radiogroup"] > label {
      background: #161c2b !important; border: 1px solid #2d3748 !important; 
      border-radius: 20px !important; padding: 8px 16px !important; cursor: pointer;
  }
  div[role="radiogroup"] > label[data-checked="true"] {
      background: #00e67615 !important; border-color: #00e676 !important;
  }
  div[role="radiogroup"] > label span[data-baseweb="radio"] { display: none !important; }
  div[role="radiogroup"] > label p { font-size: 13px !important; color: #8b949e !important; font-weight: 600 !important; margin: 0 !important; }
  div[role="radiogroup"] > label[data-checked="true"] p { color: #00e676 !important; }
  
  /* ESTILOS PARA LOS TOGGLES DE PARTIDOS */
  [data-testid="stCheckbox"] {
      background: #161c2b; padding: 10px 14px; border-radius: 8px; 
      border: 1px solid #2d3748; margin-bottom: 5px;
  }
  [data-testid="stCheckbox"] label p { color: #e1e1e1 !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ─── LECTURA DE SECRETS Y CLAVES ─────────────────────────────────
secret_gemini = st.secrets.get("GEMINI_API", "")
secret_odds = st.secrets.get("ODDS_API", "")

api_gemini_ss = secret_gemini or st.session_state.get("_gem","")
api_odds_ss   = secret_odds or st.session_state.get("_odd","")
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
    if secret_gemini and secret_odds:
        st.success("✅ Claves cargadas de forma permanente.")
        api_gemini = secret_gemini
        api_odds = secret_odds
    else:
        c1, c2 = st.columns(2)
        with c1:
            api_gemini = st.text_input("Gemini API Key", type="password", help="aistudio.google.com", key="_gem")
        with c2:
            api_odds = st.text_input("Odds API Key", type="password", help="the-odds-api.com", key="_odd")

# ─── SELECCIÓN DE LIGA (AHORA COMO BOTONES/PÍLDORAS) ─────────────
st.markdown("<p style='color:#8b949e; font-size:12px; font-weight:600; margin-bottom:5px; margin-top:10px;'>🏆 Elige la Competición</p>", unsafe_allow_html=True)

col_liga, col_btn = st.columns([4, 1])
with col_liga:
    liga_label = st.radio("Liga", list(LIGAS.keys()), horizontal=True, label_visibility="collapsed")
    liga = LIGAS[liga_label]

with col_btn:
    st.markdown('<div class="btn-actualizar">', unsafe_allow_html=True)
    if st.button("🔄 Refrescar"):
        if api_odds:
            obtener_partidos_api.clear(liga, api_odds)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─── LÓGICA DE CARGA ──────────────────────────────
upcoming_matches = []

if api_odds:
    with st.spinner("🚀 Consultando cuotas en vivo..."):
        resp, restantes = obtener_partidos_api(liga, api_odds)
        
        if isinstance(resp, list) and len(resp) > 0:
            sorted_resp = sorted(resp, key=lambda x: x.get('commence_time', ''))
            upcoming_matches = sorted_resp[:6]
        elif isinstance(resp, dict) and resp.get("message"):
             st.error(f"❌ Odds API Error: {resp['message']}")
        else:
             st.warning("⚠️ No se encontraron próximos partidos para esta competición.")

st.markdown("---")

# ─── SELECCIÓN DE PARTIDOS (AGRUPADOS POR DÍA + INTERRUPTORES) ───
st.subheader("🎯 Selecciona los partidos")

selected_matches = []

if upcoming_matches:
    # 1. Agrupar partidos por día
    partidos_por_dia = {}
    for p in upcoming_matches:
        fecha_str = fmt_fecha(p['commence_time'])
        dia = fecha_str.split(" · ")[0]  # Ej: Sáb 13 Jun
        hora = fecha_str.split(" · ")[1] # Ej: 19:00 UTC
        
        if dia not in partidos_por_dia:
            partidos_por_dia[dia] = []
        partidos_por_dia[dia].append((p, hora))
        
    # 2. Renderizar visualmente
    for dia, lista in partidos_por_dia.items():
        # Etiqueta de la Fecha
        st.markdown(f"<div style='background:#1e293b; padding:6px 12px; border-radius:6px; color:#93c5fd; font-weight:800; font-size:13px; margin-top:16px; margin-bottom:8px; border-left:4px solid #3b82f6;'>📅 {dia}</div>", unsafe_allow_html=True)
        
        # Interruptores para los partidos
        for p, hora in lista:
            home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
            away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
            
            # Usamos Toggle (Interruptor estilo iOS) 
            label_partido = f"⚽ **{home_es} vs {away_es}** *(🕒 {hora})*"
            # Generar un ID único por si el partido se repite o falla la API
            unique_key = p.get('id', p['home_team'] + p['commence_time'])
            
            if st.toggle(label_partido, key=unique_key):
                selected_matches.append(p)

    # 3. Mostrar las tarjetas de los que encendió
    if selected_matches:
        st.markdown("<br>### 📊 Análisis del Mercado", unsafe_allow_html=True)
        for i, p in enumerate(selected_matches):
            st.markdown(render_simplified_card(p, i+1), unsafe_allow_html=True)
            
        st.markdown(
            f'<div style="color:#6b7280;font-size:10px;text-align:right;'
            f'margin-top:-8px;margin-bottom:10px;">'
            f'⚡ Peticiones restantes: <strong style="color:#e1e1e1;">{restantes}</strong>/500</div>',
            unsafe_allow_html=True
        )
else:
    st.info("Ingresa tus claves API para ver los próximos partidos disponibles.")

# ─── ANÁLISIS IA (100% AUTOMATIZADO) ─────────────────────────────
st.markdown("---")

if st.button("🚀 Ejecutar Algoritmo Quant (Análisis Automático)"):
    if not api_gemini:
        st.error("❌ Falta la Gemini API Key. Ponla en Configuración.")
    elif not selected_matches:
        st.error("❌ Enciende el interruptor de al menos un partido arriba.")
    else:
        formatted_matches = []
        for p in selected_matches:
            h2h, t_over, t_under = extraer_odds(p)
            home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
            away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
            
            p_data = {
                "local": home_es,
                "visita": away_es,
                "fecha": fmt_fecha(p['commence_time'], simple=True),
                "cuotas_1x2": h2h,
                "goles_over": t_over,
                "goles_under": t_under
            }
            formatted_matches.append(p_data)

        # EL SÚPER PROMPT
        prompt = f"""
Actúa como un Analista Cuantitativo Deportivo (Quant) y Tipster Profesional Nivel Experto.
Tu objetivo es analizar estos partidos y encontrar ineficiencias de mercado o Valor Esperado Positivo (+EV).

Competición: {liga_label}
Datos de los partidos (Cuotas reales 1X2 y Goles):
{formatted_matches}

INSTRUCCIONES CLAVE (DEDUCCIÓN DE CONTEXTO):
No te proporcionaré el clima, las bajas ni la situación del torneo. TÚ DEBES deducirlo automáticamente usando tu base de conocimientos:
1. Identifica qué fase de la competición "{liga_label}" se está jugando en las fechas indicadas y la motivación real de los equipos.
2. Infiere el clima habitual de la sede en esa época del año.
3. Considera el estilo de juego histórico, técnico y físico de las selecciones/equipos involucrados.

Genera 3 estrategias de apuestas basándote en esta deducción profunda y el cruce con las cuotas reales provistas. Las justificaciones deben ser estrictamente técnicas (bloque bajo, control de posesión, transiciones, valor +EV), no uses frases genéricas.

DEBES responder ÚNICAMENTE con un objeto JSON válido usando esta estructura exacta:

{{
  "game_script": "Explica brevemente el contexto que has deducido (torneo, clima estimado, situación táctica) y cómo afectará el ritmo de juego (máx 4 líneas).",
  "estrategias": [
    {{
      "nivel": "🛡️ La Apuesta Segura (Protección de Bankroll)",
      "picks": [
        {{"partido": "Local vs Visita", "seleccion": "Mercado elegido", "cuota": "1.50"}}
      ],
      "cuota_total": "1.50",
      "justificacion": "Análisis cuantitativo de por qué esta cuota tiene valor real..."
    }},
    {{
      "nivel": "⚖️ La Apuesta Moderada (Valor Esperado +EV)",
      "picks": [
        {{"partido": "Local vs Visita", "seleccion": "Mercado", "cuota": "1.80"}},
        {{"partido": "Local vs Visita", "seleccion": "Mercado", "cuota": "1.30"}}
      ],
      "cuota_total": "2.34",
      "justificacion": "Tesis táctica del pick..."
    }},
    {{
      "nivel": "🔥 La Apuesta Arriesgada (Ineficiencia de Mercado)",
      "picks": [
        {{"partido": "Local vs Visita", "seleccion": "Mercado", "cuota": "2.10"}},
        {{"partido": "Local vs Visita", "seleccion": "Mercado", "cuota": "3.00"}}
      ],
      "cuota_total": "6.30",
      "justificacion": "Explicación del riesgo y recompensa matemática..."
    }}
  ]
}}
"""
        with st.spinner("🧠 Deduciendo contexto táctico y calculando Valor Esperado..."):
            try:
                client = genai.Client(api_key=api_gemini)
                resp = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=4096, 
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                
                data = json.loads(resp.text)
                
                st.markdown("### 📈 El Veredicto del Algoritmo")
                
                st.markdown(f"""
                <div style="background:#0d1117; border-left:4px solid #8b5cf6; padding:14px 16px; border-radius:8px; margin-bottom:20px;">
                    <div style="color:#a78bfa; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">⚡ Game Script (Contexto Deducido)</div>
                    <div style="font-size:14px; color:#e1e1e1; line-height:1.5;"><i>"{data.get('game_script', '')}"</i></div>
                </div>
                """, unsafe_allow_html=True)
                
                tabs = st.tabs(["🛡️ Segura", "⚖️ Moderada", "🔥 Arriesgada"])
                
                for i, tab in enumerate(tabs):
                    with tab:
                        est = data['estrategias'][i]
                        
                        picks_html = ""
                        for pick in est['picks']:
                            picks_html += f"""<div style="background:#0f172a; padding:12px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; border:1px solid #1e293b;">
<div style="display:flex; flex-direction:column;">
<span style="color:#8b949e; font-size:11px; font-weight:700;">⚽ {pick['partido']}</span>
<span style="color:#e1e1e1; font-size:14px; font-weight:600; margin-top:2px;">{pick['seleccion']}</span>
</div>
<span style="background:#10b981; color:#0f172a; padding:4px 10px; border-radius:6px; font-weight:800; font-size:13px;">@{pick['cuota']}</span>
</div>"""
                        
                        st.markdown(f"""<div style="background:#161c2b; border:2px dashed #2d3748; border-radius:12px; padding:16px; margin-top:8px;">
<h4 style="color:#f8fafc; margin-top:0; border-bottom:1px solid #2d3748; padding-bottom:10px; margin-bottom:16px;">{est['nivel']}</h4>
{picks_html}
<div style="display:flex; justify-content:flex-end; margin-top:16px; margin-bottom:16px;">
<div style="background:#8b5cf615; border:1px solid #8b5cf6; padding:8px 16px; border-radius:8px;">
<span style="color:#c4b5fd; font-size:12px; font-weight:700;">CUOTA TOTAL APROX:</span>
<span style="color:#a78bfa; font-size:18px; font-weight:900; margin-left:8px;">@{est['cuota_total']}</span>
</div>
</div>
<div style="background:#1e293b; padding:12px; border-radius:8px; border-left:3px solid #f59e0b;">
<span style="color:#fcd34d; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:1px;">Tesis Cuantitativa (+EV)</span>
<p style="color:#cbd5e1; font-size:13px; line-height:1.5; margin-top:6px; margin-bottom:0;">{est['justificacion']}</p>
</div>
</div>""", unsafe_allow_html=True)
                        
            except Exception as e:
                st.error(f"❌ Error al procesar respuesta de la IA. Intenta de nuevo. Detalle: {e}")

st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
