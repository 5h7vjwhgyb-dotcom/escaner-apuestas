import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
import json

# Manejo seguro de Zona Horaria de Chile
try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-4))

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
    "🇬🇧 Premier League":                 "soccer_epl",
    "🇪🇸 La Liga":                        "soccer_spain_la_liga",
    "🇩🇪 Bundesliga":                     "soccer_germany_bundesliga",
    "🇮🇹 Serie A":                        "soccer_italy_serie_a",
    "🇫🇷 Ligue 1":                        "soccer_france_ligue_one",
    "🏆 Champions League":                "soccer_uefa_champs_league",
}

# ═══════════════════════════════════════════════
# FUNCIONES API CON CACHÉ 
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

@st.cache_data(ttl=43200, show_spinner=False)
def obtener_calendario_apisports(fecha_str, api_key):
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": api_key, "x-apisports-host": "v3.football.api-sports.io"}
    try:
        resp = requests.get(url, headers=headers, params={"date": fecha_str}, timeout=10)
        return resp.json().get("response", [])
    except:
        return []

@st.cache_data(ttl=43200, show_spinner=False)
def obtener_estadisticas_apisports(fixture_id, api_key):
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    headers = {"x-apisports-key": api_key, "x-apisports-host": "v3.football.api-sports.io"}
    try:
        resp = requests.get(url, headers=headers, params={"fixture": fixture_id}, timeout=10)
        return resp.json().get("response", [])
    except:
        return []

# ═══════════════════════════════════════════════
# CLAVES API SEGURAS (DESDE SECRETS)
# ═══════════════════════════════════════════════
api_gemini = st.secrets.get("GEMINI_API", "")
api_odds = st.secrets.get("ODDS_API", "")
api_sports = st.secrets.get("SPORTS_API", "")

online = bool(api_gemini and api_odds and api_sports)

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
                    if o["name"] == home and (h2h["home"] is None or p > h2h["home"]): h2h["home"] = round(p,2)
                    elif o["name"] == away and (h2h["away"] is None or p > h2h["away"]): h2h["away"] = round(p,2)
                    elif o["name"] == "Draw" and (h2h["draw"] is None or p > h2h["draw"]): h2h["draw"] = round(p,2)
            elif mkt["key"] == "totals":
                for o in mkt["outcomes"]:
                    pt = o.get("point", 2.5); p = o["price"]
                    if o["name"] == "Over" and (pt not in t_over or p > t_over[pt]): t_over[pt] = round(p,2)
                    elif o["name"] == "Under" and (pt not in t_under or p > t_under[pt]): t_under[pt] = round(p,2)
                        
    return h2h, t_over, t_under

def calcular_probs(h2h):
    if not all(v is not None for v in h2h.values()):
        return {"home":40,"draw":30,"away":30}
    ph, pd, pa = 1/h2h["home"], 1/h2h["draw"], 1/h2h["away"]
    total = ph + pd + pa
    hp = round(ph/total*100)
    dp = round(pd/total*100)
    return {"home": hp, "draw": dp, "away": 100 - hp - dp}

def fmt_fecha(iso, simple=False):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        dt_chile = dt.astimezone(TZ_CHILE)
        if simple: return dt_chile.strftime('%Y-%m-%d')
        dias = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt_chile.isoweekday()%7]} {dt_chile.day} {meses[dt_chile.month]} · {dt_chile.strftime('%H:%M')} (Chile)"
    except: return "Fecha no disponible · 00:00 (Chile)"

def cruzar_datos(partido, dia_sports, api_sports_key):
    if not dia_sports: return "Sin datos API-Sports"
    
    local_norm = partido['home_team'].lower()[:6]
    for p_sports in dia_sports:
        if local_norm in p_sports['teams']['home']['name'].lower():
            fix_id = p_sports['fixture']['id']
            stats = obtener_estadisticas_apisports(fix_id, api_sports_key)
            return {
                "estadio": p_sports['fixture']['venue']['name'],
                "arbitro": p_sports['fixture']['referee'],
                "estado_local": p_sports['teams']['home'].get('winner'),
                "estadisticas_tacticas_historicas": stats
            }
    return "No hubo coincidencia en la jornada"

def render_simplified_card(partido, idx=1):
    home_en = partido.get("home_team","Local")
    away_en = partido.get("away_team","Visita")
    home_es = TRADUCCIONES.get(home_en, home_en)
    away_es = TRADUCCIONES.get(away_en, away_en)
    fecha = fmt_fecha(partido.get("commence_time",""))
    h2h, _, _ = extraer_odds(partido)
    probs = calcular_probs(h2h)
    
    hp, dp, ap = probs["home"], probs["draw"], probs["away"]
    odd_h = f"@{h2h['home']}" if h2h.get('home') else "N/A"
    odd_d = f"@{h2h['draw']}" if h2h.get('draw') else "N/A"
    odd_a = f"@{h2h['away']}" if h2h.get('away') else "N/A"

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
</div>"""

# ═══════════════════════════════════════════════════════════════
# APP UI Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡COMBINADAS", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  [data-testid="stAppViewContainer"]  { background:#0d1117 !important; }
  [data-testid="stHeader"]            { background:transparent !important; }
  .block-container { padding-top:0.8rem !important; max-width:560px !important; }
  label, .stTextInput label { color:#8b949e !important; font-size:12px !important; font-weight:600 !important; }
  .stTextInput input { background:#161c2b !important; color:#e1e1e1 !important; border:1px solid #2d3748 !important; border-radius:10px !important; }
  [data-testid="stExpander"] { background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:12px !important; }
  [data-testid="stExpanderToggleIcon"] svg { fill:#00e676 !important; }
  .stButton > button { background:linear-gradient(90deg,#00e676,#00b4d8) !important; border:none !important; border-radius:12px !important; color:#0d1117 !important; font-weight:800 !important; font-size:14px !important; width:100% !important; padding:0.65em !important; }
  .stButton > button:hover { opacity:.9; }
  [data-testid="stCheckbox"] { background: #161c2b; padding: 10px 14px; border-radius: 8px; border: 1px solid #2d3748; margin-bottom: 5px; }
  [data-testid="stCheckbox"] label p { color: #e1e1e1 !important; font-size: 14px !important; }
  hr { border-color:#2d3748 !important; }
</style>
""", unsafe_allow_html=True)

bcol = "#22c55e" if online else "#ef4444"
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;background:#161c2b;padding:13px 16px;border-radius:14px;margin-bottom:16px;border:1px solid #2d3748;">
  <span style="font-size:20px;font-weight:900;color:#e1e1e1;letter-spacing:.5px;">BET<span style="color:#00e676;">⚡</span>COMBINADAS</span>
  <span style="border:1px solid {bcol};color:{bcol};font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:.5px;">{'🟢 EN LÍNEA' if online else '🔴 FALTAN CLAVES'}</span>
</div>
""", unsafe_allow_html=True)

if not online:
    st.warning("⚠️ Asegúrate de cargar tus claves (GEMINI_API, ODDS_API, SPORTS_API) en los secretos de tu entorno (ej. Streamlit Cloud).")

# ─── SELECCIÓN DE LIGA Y CARGA DE PARTIDOS ─────────────────────────────
st.markdown("<p style='color:#8b949e; font-size:12px; font-weight:600; margin-bottom:5px;'>🏆 Competición</p>", unsafe_allow_html=True)
liga_label = st.selectbox("", list(LIGAS.keys()), label_visibility="collapsed")
liga = LIGAS[liga_label]

upcoming_matches = []
if api_odds:
    with st.spinner("Consultando cuotas en vivo..."):
        resp, restantes = obtener_partidos_api(liga, api_odds)
        if isinstance(resp, list) and len(resp) > 0:
            upcoming_matches = sorted(resp, key=lambda x: x.get('commence_time', ''))[:5]
        elif isinstance(resp, dict) and resp.get("message"):
            st.error(f"❌ Error Odds API: {resp['message']}")

# ─── SELECCIÓN ───────────────────
selected_matches = []
if upcoming_matches:
    st.markdown("### 🎯 Selecciona el Partido a Analizar")
    for p in upcoming_matches:
        home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
        away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
        hora = fmt_fecha(p['commence_time']).split(" · ")[1]
        
        if st.toggle(f"⚽ **{home_es} vs {away_es}** *(🕒 {hora})*", key=p.get('id')):
            selected_matches.append(p)
            
    for i, p in enumerate(selected_matches):
        st.markdown(render_simplified_card(p, i+1), unsafe_allow_html=True)

# ─── ANÁLISIS IA + CRUCE DE DATOS ─────────────────────────────
st.markdown("---")

if st.button("🚀 Generar Análisis Cuantitativo"):
    if not online: st.error("❌ Faltan Claves API en los secretos del sistema.")
    elif not selected_matches: st.error("❌ Selecciona al menos un partido.")
    else:
        # 1. Obtener la fecha del primer partido para API-Sports
        fecha_req = fmt_fecha(selected_matches[0]['commence_time'], simple=True)
        
        with st.spinner("📡 Cruzando datos tácticos en vivo con API-Sports..."):
            calendario_dia = obtener_calendario_apisports(fecha_req, api_sports)
            
            formatted_matches = []
            for p in selected_matches:
                h2h, t_over, t_under = extraer_odds(p)
                stats_avanzadas = cruzar_datos(p, calendario_dia, api_sports)
                
                formatted_matches.append({
                    "local": TRADUCCIONES.get(p['home_team'], p['home_team']),
                    "visita": TRADUCCIONES.get(p['away_team'], p['away_team']),
                    "cuotas": {"1X2": h2h, "Goles_Over": t_over, "Goles_Under": t_under},
                    "datos_tacticos_apisports": stats_avanzadas
                })
        
        prompt = f"""
Actúa como un Analista Cuantitativo Deportivo (Quant).
Cruza las cuotas de The Odds API con los datos tácticos de API-Sports para encontrar Valor Esperado Positivo (+EV).

Competición: {liga_label}
Datos de los partidos:
{json.dumps(formatted_matches)}

INSTRUCCIONES CLAVE:
1. Analiza ritmo de juego y remates para deducir mercado de Córners y Tiros.
2. Evalúa agresividad para proponer línea de Tarjetas.
3. Evalúa mercado de Jugadores buscando probabilidad alta (Ej: Erling Haaland anota, Harry Kane más 1.5 remates a puerta).
4. Elige un ganador claro con Hándicap si aplica.

Responde ÚNICAMENTE con este JSON para cada partido:
{{
  "partido": "Nombre Local vs Nombre Visita",
  "analisis_general": "Breve tesis táctica en 3 líneas.",
  "mercados": {{
    "principal": {{ "1x2_o_doble": "Pronóstico", "handicap": "Línea sugerida y cuota est." }},
    "goles": {{ "linea_exacta": "Over/Under X.5", "gol_primer_tiempo": "Sí/No" }},
    "estadisticas": {{ "corners": "Over X.5", "tarjetas": "Over/Under", "remates_puerta": "Línea proyectada" }},
    "jugador_estrella": {{ "pick": "Nombre Jugador - Mercado", "justificacion": "Por qué tiene valor" }}
  }}
}}
"""
        with st.spinner("🧠 El algoritmo de Gemini está procesando los vectores tácticos..."):
            try:
                client = genai.Client(api_key=api_gemini)
                resp = client.models.generate_content(
                    model="gemini-2.0-flash", # <--- MODELO ACTUALIZADO AQUÍ
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=4000, 
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                
                # Transformar JSON a UI
                datos_ia = json.loads(resp.text)
                if isinstance(datos_ia, dict): datos_ia = [datos_ia] # Por si devuelve 1 solo objeto
                
                for analisis in datos_ia:
                    st.markdown(f"### 🛡️ {analisis.get('partido', 'Pronóstico')}")
                    st.markdown(f"<div style='background:#1e293b; padding:12px; border-left:4px solid #8b5cf6; border-radius:6px; color:#e1e1e1; font-size:13px; margin-bottom:16px;'><i>{analisis.get('analisis_general', '')}</i></div>", unsafe_allow_html=True)
                    
                    m = analisis.get('mercados', {})
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        st.markdown("<h5 style='color:#00e676;'>🏆 Mercado Principal</h5>", unsafe_allow_html=True)
                        st.info(f"**Resultado:** {m.get('principal', {}).get('1x2_o_doble', 'N/A')}\n\n**Hándicap:** {m.get('principal', {}).get('handicap', 'N/A')}")
                        
                        st.markdown("<h5 style='color:#00b4d8;'>⚽ Mercado Goles</h5>", unsafe_allow_html=True)
                        st.success(f"**Línea:** {m.get('goles', {}).get('linea_exacta', 'N/A')}\n\n**Gol 1T:** {m.get('goles', {}).get('gol_primer_tiempo', 'N/A')}")
                        
                    with c2:
                        st.markdown("<h5 style='color:#f59e0b;'>📊 Mercado Estadísticas</h5>", unsafe_allow_html=True)
                        st.warning(f"**Córners:** {m.get('estadisticas', {}).get('corners', 'N/A')}\n\n**Tarjetas:** {m.get('estadisticas', {}).get('tarjetas', 'N/A')}\n\n**Remates:** {m.get('estadisticas', {}).get('remates_puerta', 'N/A')}")
                        
                        st.markdown("<h5 style='color:#ec4899;'>🔥 Player Props</h5>", unsafe_allow_html=True)
                        st.error(f"**Pick:** {m.get('jugador_estrella', {}).get('pick', 'N/A')}\n\n*{m.get('jugador_estrella', {}).get('justificacion', 'N/A')}*")
                    
                    st.markdown("---")
            except Exception as e:
                st.error(f"Error procesando el análisis: {str(e)}")
