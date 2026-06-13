import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
import math
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
    "Slovenia": "Eslovenia", "Ireland": "Irlanda", "New Caledonia": "N. Caledonia",
    "Curacao": "Curaçao"
}

BANDERAS = {
    "Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷", "Korea Republic":"🇰🇷",
    "Czechia":"🇨🇿","Czech Republic":"🇨🇿","USA":"🇺🇸",
    "United States":"🇺🇸","Paraguay":"🇵🇾","Canada":"🇨🇦",
    "Bosnia and Herzegovina":"🇧🇦", "Bosnia & Herzegovina":"🇧🇦", "Qatar":"🇶🇦",
    "Switzerland":"🇨🇭","Australia":"🇦🇺","Turkey":"🇹🇷","Turkiye":"🇹🇷",
    "Germany":"🇩🇪","Curacao":"🇨🇼","Curaçao":"🇨🇼","Ivory Coast":"🇨🇮","Ecuador":"🇪🇨",
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
# FUNCIONES CON CACHÉ DE DISCO (LAS 3 APIs)
# ═══════════════════════════════════════════════
@st.cache_data(ttl=21600, persist="disk", show_spinner=False)
def obtener_partidos_api(liga, api_key):
    mercados = "h2h,totals,spreads"
    url = (f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
           f"?apiKey={api_key}&regions=eu&markets={mercados}")
    try:
        resp_raw = requests.get(url, timeout=10)
        restantes = resp_raw.headers.get("x-requests-remaining", "?")
        return resp_raw.json(), restantes
    except Exception as e:
        return {"message": str(e)}, "?"

@st.cache_data(ttl=43200, persist="disk", show_spinner=False)
def obtener_estadisticas_futbol(local_nombre, visita_nombre, api_key):
    if not api_key:
        return {"error": "Falta la Football API Key"}
        
    headers = { 'X-Auth-Token': api_key }
    stats = {
        "estado_forma_local": "Desconocido",
        "estado_forma_visita": "Desconocido",
        "posicion_local": "N/A",
        "posicion_visita": "N/A"
    }
    
    try:
        url = "https://api.football-data.org/v4/matches?dateFrom={hoy}&dateTo={futuro}"
        hoy_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        futuro_str = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        url_formateada = url.format(hoy=hoy_str, futuro=futuro_str)
        
        resp = requests.get(url_formateada, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"error": f"Error API Fútbol: {resp.status_code}"}
            
        data = resp.json()
        
        for match in data.get("matches", []):
            home_api = match["homeTeam"]["shortName"] or match["homeTeam"]["name"]
            away_api = match["awayTeam"]["shortName"] or match["awayTeam"]["name"]
            
            if (local_nombre.lower() in home_api.lower() or home_api.lower() in local_nombre.lower()) and \
               (visita_nombre.lower() in away_api.lower() or away_api.lower() in visita_nombre.lower()):
                
                stats["estado_forma_local"] = match.get("homeTeam", {}).get("form", "N/A")
                stats["estado_forma_visita"] = match.get("awayTeam", {}).get("form", "N/A")
                
                url_st = f"https://api.football-data.org/v4/competitions/{match['competition']['code']}/standings"
                resp_st = requests.get(url_st, headers=headers, timeout=10)
                
                if resp_st.status_code == 200:
                    standings_data = resp_st.json()
                    for table in standings_data.get("standings", []):
                        if table["type"] == "TOTAL":
                            for team_row in table["table"]:
                                if team_row["team"]["id"] == match["homeTeam"]["id"]:
                                    stats["posicion_local"] = f"{team_row['position']}° ({team_row['points']} pts, GF:{team_row['goalsFor']} GC:{team_row['goalsAgainst']})"
                                elif team_row["team"]["id"] == match["awayTeam"]["id"]:
                                    stats["posicion_visita"] = f"{team_row['position']}° ({team_row['points']} pts, GF:{team_row['goalsFor']} GC:{team_row['goalsAgainst']})"
                break 
        return stats
    except Exception as e:
        return {"error": f"Fallo Football-Data: {str(e)}"}

@st.cache_data(ttl=86400, persist="disk", show_spinner=False)
def obtener_analisis_ia(api_key, prompt, id_combinacion):
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=4096,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    return json.loads(resp.text)

# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def flag(team): return BANDERAS.get(team, "🏳️")

def extraer_odds(partido):
    home = partido.get("home_team","")
    away = partido.get("away_team","")
    h2h = {"home":None,"draw":None,"away":None}
    t_over, t_under = {}, {}
    otros_mercados = {}
    
    for bk in partido.get("bookmakers",[]):
        for mkt in bk.get("markets",[]):
            mk_key = mkt["key"]
            if mk_key == "h2h":
                for o in mkt["outcomes"]:
                    p = o["price"]
                    if o["name"] == home:
                        if h2h["home"] is None or p > h2h["home"]: h2h["home"] = round(p,2)
                    elif o["name"] == away:
                        if h2h["away"] is None or p > h2h["away"]: h2h["away"] = round(p,2)
                    elif o["name"] == "Draw":
                        if h2h["draw"] is None or p > h2h["draw"]: h2h["draw"] = round(p,2)
            elif mk_key == "totals":
                for o in mkt["outcomes"]:
                    pt = o.get("point", 2.5); p = o["price"]
                    if o["name"] == "Over":
                        if pt not in t_over or p > t_over[pt]: t_over[pt] = round(p,2)
                    else:
                        if pt not in t_under or p > t_under[pt]: t_under[pt] = round(p,2)
            else:
                if mk_key not in otros_mercados:
                    otros_mercados[mk_key] = {}
                for o in mkt["outcomes"]:
                    nombre = o["name"]
                    punto = o.get("point", "")
                    desc = o.get("description", "")
                    label = f"{nombre} {punto} {desc}".strip()
                    precio = round(o["price"], 2)
                    if label not in otros_mercados[mk_key] or precio > otros_mercados[mk_key][label]:
                        otros_mercados[mk_key][label] = precio
                        
    return h2h, t_over, t_under, otros_mercados

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
        dt_chile = dt.astimezone(TZ_CHILE)
        if simple: return dt_chile.strftime('%Y-%m-%d')
        dias = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt_chile.isoweekday()%7]} {dt_chile.day} {meses[dt_chile.month]} · {dt_chile.strftime('%H:%M')} (Chile)"
    except: return "Fecha no disponible · 00:00 (Chile)"

def render_simplified_card(partido, idx=1):
    home_en = partido.get("home_team","Local")
    away_en = partido.get("away_team","Visita")
    home_es = TRADUCCIONES.get(home_en, home_en)
    away_es = TRADUCCIONES.get(away_en, away_en)
    fecha = fmt_fecha(partido.get("commence_time",""))
    
    h2h, t_over, t_under, _ = extraer_odds(partido)
    probs = calcular_probs(h2h)
    best = mejor_apuesta(h2h, probs, t_over, t_under, home_es, away_es)
    hp, dp, ap = probs["home"], probs["draw"], probs["away"]
    
    odd_h = f"{h2h['home']}" if h2h.get('home') else "N/A"
    odd_d = f"{h2h['draw']}" if h2h.get('draw') else "N/A"
    odd_a = f"{h2h['away']}" if h2h.get('away') else "N/A"

    best_bet_html = ""
    if best:
        best_bet_html = f"""<div style="background:#00e67615; color:#00e676; border:1px solid #00e67660; padding:8px; border-radius:8px; font-size:13px; font-weight:800; text-align:center; margin-top:16px; box-shadow: 0 2px 8px rgba(0,230,118,0.1);">💡 Valor Matemático: {best['label']} ({best['odds']})</div>"""

    return f"""<div style="background:#161c2b;border-radius:12px;padding:16px;border:1px solid #2a3349;margin-bottom:14px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;box-shadow:0 4px 6px rgba(0,0,0,0.2);">
    
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <span style="color:#8b949e;font-size:12px;font-weight:600;">📅 {fecha}</span>
        <span style="background:#2d3748;color:#e1e1e1;font-size:10px;padding:3px 8px;border-radius:20px;font-weight:800;">M {idx}</span>
    </div>
    
    <div style="display:flex;align-items:flex-end;margin-bottom:16px;">
        <div style="flex:1;text-align:center; display:flex; flex-direction:column; align-items:center;">
            <div style="font-size:36px;line-height:1.1;margin-bottom:6px;">{flag(home_en)}</div>
            <div style="color:#e1e1e1;font-weight:700;font-size:13px;margin-bottom:8px;">{home_es}</div>
            <div style="background:#22c55e15; border:1px solid #22c55e50; color:#22c55e; padding:4px 12px; border-radius:6px; font-size:14px; font-weight:800;">{odd_h}</div>
        </div>
        
        <div style="flex:1;text-align:center; display:flex; flex-direction:column; align-items:center; justify-content:flex-end;">
            <div style="color:#8b949e;font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:8px;">EMPATE</div>
            <div style="background:#4b556330; border:1px solid #4b556380; color:#e1e1e1; padding:4px 12px; border-radius:6px; font-size:14px; font-weight:800;">{odd_d}</div>
        </div>
        
        <div style="flex:1;text-align:center; display:flex; flex-direction:column; align-items:center;">
            <div style="font-size:36px;line-height:1.1;margin-bottom:6px;">{flag(away_en)}</div>
            <div style="color:#e1e1e1;font-weight:700;font-size:13px;margin-bottom:8px;">{away_es}</div>
            <div style="background:#ef444415; border:1px solid #ef444450; color:#ef4444; padding:4px 12px; border-radius:6px; font-size:14px; font-weight:800;">{odd_a}</div>
        </div>
    </div>
    
    <div style="display:flex;border-radius:6px;overflow:hidden;height:24px;box-shadow:inset 0 1px 3px rgba(0,0,0,0.3);">
        <div style="background:#22c55e;width:{hp}%;display:flex;align-items:center;justify-content:center;color:#0d1117;font-size:11px;font-weight:900;min-width:24px;">{hp}%</div>
        <div style="background:#4b5563;width:{dp}%;display:flex;align-items:center;justify-content:center;color:#e1e1e1;font-size:11px;font-weight:700;min-width:24px;">{dp}%</div>
        <div style="background:#ef4444;width:{ap}%;display:flex;align-items:center;justify-content:center;color:#0d1117;font-size:11px;font-weight:900;min-width:24px;">{ap}%</div>
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

  label, .stTextInput label, .stTextArea label { color:#8b949e !important; font-size:12px !important; font-weight:600 !important; }
  .stTextInput input, .stTextArea textarea { background:#161c2b !important; color:#e1e1e1 !important; border:1px solid #2d3748 !important; border-radius:10px !important; font-size:13px !important; }
  [data-testid="stSelectbox"] > div > div { background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:10px !important; color:#e1e1e1 !important; }
  [data-testid="stExpander"] { background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:12px !important; }
  [data-testid="stExpanderToggleIcon"] svg { fill:#00e676 !important; }

  .stButton > button { background:linear-gradient(90deg,#00e676,#00b4d8) !important; border:none !important; border-radius:12px !important; color:#0d1117 !important; font-weight:800 !important; font-size:14px !important; width:100% !important; padding:0.65em !important; }
  .stButton > button:hover { opacity:.9; }
  .btn-actualizar > button { background:#2d3748 !important; color:#e1e1e1 !important; font-size:12px !important; margin-top: 25px !important; }
  [data-testid="stAlert"] { border-radius:12px !important; }
  hr { border-color:#2d3748 !important; }
  
  [data-testid="stTabs"] button { background-color: #161c2b !important; color: #8b949e !important; font-weight: 700 !important; border-radius: 8px !important; border: 1px solid #2d3748 !important; padding: 6px 16px !important; margin-right: 8px !important; }
  [data-testid="stTabs"] button[aria-selected="true"] { background-color: #00e67615 !important; color: #00e676 !important; border: 1px solid #00e676 !important; box-shadow: 0 0 10px rgba(0,230,118,0.1) !important; }
  
  div[role="radiogroup"] { gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  div[role="radiogroup"] > label { background: #161c2b !important; border: 1px solid #2d3748 !important; border-radius: 20px !important; padding: 8px 16px !important; cursor: pointer; }
  div[role="radiogroup"] > label[data-checked="true"] { background: #00e67615 !important; border-color: #00e676 !important; }
  div[role="radiogroup"] > label span[data-baseweb="radio"] { display: none !important; }
  div[role="radiogroup"] > label p { font-size: 13px !important; color: #8b949e !important; font-weight: 600 !important; margin: 0 !important; }
  div[role="radiogroup"] > label[data-checked="true"] p { color: #00e676 !important; }
  
  [data-testid="stCheckbox"] { background: #161c2b; padding: 10px 14px; border-radius: 8px; border: 1px solid #2d3748; margin-bottom: 5px; }
  [data-testid="stCheckbox"] label p { color: #e1e1e1 !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ─── LECTURA DE SECRETS Y CLAVES ─────────────────────────────────
try:
    secret_gemini = st.secrets.get("GEMINI_API", "")
    secret_odds = st.secrets.get("ODDS_API", "")
    secret_football = st.secrets.get("FOOTBALL_API", "")
except FileNotFoundError:
    secret_gemini = ""
    secret_odds = ""
    secret_football = ""

api_gemini_ss = secret_gemini or st.session_state.get("_gem","")
api_odds_ss   = secret_odds or st.session_state.get("_odd","")
api_foot_ss   = secret_football or st.session_state.get("_foot","")

online = bool(api_gemini_ss and api_odds_ss)
dot    = "🟢" if online else "🔴"
badge  = "EN LÍNEA" if online else "SIN CONEXIÓN"
bcol   = "#22c55e" if online else "#ef4444"

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;background:#161c2b;padding:13px 16px;border-radius:14px;margin-bottom:16px;border:1px solid #2d3748;">
  <span style="font-size:20px;font-weight:900;color:#e1e1e1;letter-spacing:.5px;">BET<span style="color:#00e676;">⚡</span>COMBINADAS</span>
  <span style="border:1px solid {bcol};color:{bcol};font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:.5px;">{dot} {badge}</span>
</div>
""", unsafe_allow_html=True)

with st.expander("⚙️ Configuración — Claves API", expanded=not online):
    if secret_gemini and secret_odds and secret_football:
        st.success("✅ Claves cargadas de forma permanente.")
        api_gemini = secret_gemini
        api_odds = secret_odds
        api_football = secret_football
    else:
        c1, c2, c3 = st.columns(3)
        with c1: api_gemini = st.text_input("Gemini API", type="password", key="_gem")
        with c2: api_odds = st.text_input("Odds API", type="password", key="_odd")
        with c3: api_football = st.text_input("Football API", type="password", key="_foot")

# ─── SELECCIÓN DE LIGA ─────────────────────────────
st.markdown("<p style='color:#8b949e; font-size:12px; font-weight:600; margin-bottom:5px; margin-top:10px;'>🏆 Elige la Competición</p>", unsafe_allow_html=True)
col_liga, col_btn = st.columns([4, 1])
with col_liga:
    liga_label = st.radio("Liga", list(LIGAS.keys()), horizontal=True, label_visibility="collapsed")
    liga = LIGAS[liga_label]
with col_btn:
    st.markdown('<div class="btn-actualizar">', unsafe_allow_html=True)
    if st.button("🔄 Refrescar"):
        if api_odds: obtener_partidos_api.clear(liga, api_odds); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─── LÓGICA DE CARGA ──────────────────────────────
upcoming_matches = []
if api_odds_ss:
    resp, restantes = obtener_partidos_api(liga, api_odds_ss)
    if isinstance(resp, list) and len(resp) > 0:
        upcoming_matches = sorted(resp, key=lambda x: x.get('commence_time', ''))[:6]

st.markdown("---")

# ─── SELECCIÓN DE PARTIDOS ───────────────────
st.subheader("🎯 Selecciona los partidos")
selected_matches = []

if upcoming_matches:
    partidos_por_dia = {}
    for p in upcoming_matches:
        fecha_str = fmt_fecha(p['commence_time'])
        dia = fecha_str.split(" · ")[0]
        hora = fecha_str.split(" · ")[1]
        if dia not in partidos_por_dia: partidos_por_dia[dia] = []
        partidos_por_dia[dia].append((p, hora))
        
    for dia, lista in partidos_por_dia.items():
        st.markdown(f"<div style='background:#1e293b; padding:6px 12px; border-radius:6px; color:#93c5fd; font-weight:800; font-size:13px; margin-top:16px; margin-bottom:8px; border-left:4px solid #3b82f6;'>📅 {dia}</div>", unsafe_allow_html=True)
        for p, hora in lista:
            home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
            away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
            if st.toggle(f"⚽ **{home_es} vs {away_es}** *(🕒 {hora})*", key=p.get('id', p['home_team']+p['commence_time'])):
                selected_matches.append(p)

    if selected_matches:
        st.markdown("<br>### 📊 Análisis del Mercado", unsafe_allow_html=True)
        for i, p in enumerate(selected_matches):
            st.markdown(render_simplified_card(p, i+1), unsafe_allow_html=True)
else:
    if api_odds_ss and isinstance(resp, dict) and "message" in resp:
        st.error(f"❌ El servidor de The-Odds-API dice: {resp['message']}")
    elif api_odds_ss:
        st.warning("⚠️ La conexión fue exitosa, pero no hay partidos con cuotas disponibles para esta liga en este momento. Intenta elegir otra competición arriba.")
    else:
        st.info("Ingresa tus claves API para ver los próximos partidos disponibles.")

# ═══════════════════════════════════════════════════════════════
# ANÁLISIS IA CON RAZONAMIENTO POR PICK + PICKS DESTACADOS
# ═══════════════════════════════════════════════════════════════
st.markdown("---")

if st.button("🚀 Ejecutar Algoritmo Quant (Análisis Automático)"):
    if not api_gemini_ss: st.error("❌ Falta la Gemini API Key.")
    elif not selected_matches: st.error("❌ Enciende el interruptor de al menos un partido.")
    else:
        formatted_matches = []
        partidos_ids = []
        
        with st.spinner("⏳ Extrayendo estadísticas de Football-Data y cruzando con casas de apuestas..."):
            for p in selected_matches:
                h2h, t_over, t_under, otros = extraer_odds(p)
                home_es = TRADUCCIONES.get(p['home_team'], p['home_team'])
                away_es = TRADUCCIONES.get(p['away_team'], p['away_team'])
                partidos_ids.append(f"{home_es}-{away_es}")
                
                stats_futbol = {}
                if api_foot_ss:
                    stats_futbol = obtener_estadisticas_futbol(home_es, away_es, api_foot_ss)
                
                formatted_matches.append({
                    "local": home_es, "visita": away_es, "fecha": fmt_fecha(p['commence_time'], simple=True),
                    "estadisticas_reales_equipo": stats_futbol,
                    "cuotas_1x2": h2h, "goles_over": t_over, "goles_under": t_under,
                    "otros_mercados": otros
                })

        id_combinacion = ",".join(sorted(partidos_ids))

        # ── PROMPT ACTUALIZADO CON CADENA DE RAZONAMIENTO ──────────────
        prompt = f"""
Eres un Analista Cuantitativo Deportivo de élite. Tu misión es identificar selecciones GANADORAS y RENTABLES, no solo matemáticamente interesantes. Piensa de forma estructurada antes de proponer cada pick.

Competición: {liga_label}
Datos completos de los partidos (cuotas reales + estadísticas en tiempo real):
{json.dumps(formatted_matches, ensure_ascii=False, indent=2)}

══════════════════════════════════════════════════════════════
METODOLOGÍA DE RAZONAMIENTO OBLIGATORIA — APLICA A CADA PICK
══════════════════════════════════════════════════════════════
Antes de seleccionar cualquier pick, razona en 3 pasos y documéntalos:

🔍 PASO 1 – DIAGNÓSTICO DEPORTIVO:
Evalúa el contexto real del partido: forma reciente del equipo (W/D/L), posición en tabla, promedio goles a favor/contra, ventaja de local/visita y cualquier factor contextual determinante. ¿Quién domina claramente y por qué?

📊 PASO 2 – LECTURA DEL MERCADO:
¿La cuota ofrecida refleja fielmente la probabilidad real, o hay una ineficiencia explotable? Compara la probabilidad implícita de la cuota (1/cuota) con tu probabilidad real estimada. Si tu probabilidad real > probabilidad implícita, hay +EV (valor positivo esperado).

✅ PASO 3 – VEREDICTO GANADOR:
¿Por qué esta selección tiene alta probabilidad de ocurrir? ¿Cuál es el escenario negativo y qué tan probable es? ¿La relación riesgo/ganancia justifica apostar en ella? Da un veredicto claro y directo.

══════════════════════════════════════════════════════════════
PICKS ESPECIALES OBLIGATORIOS (Adicionales a las 3 estrategias)
══════════════════════════════════════════════════════════════

⭐ PICK ESTRELLA DEL DÍA:
Tu UNA mejor recomendación absoluta. El pick donde convergen: mayor valor (+EV), respaldo estadístico sólido, y cuota con ineficiencia detectable. No importa si es de cuota baja o media, importa que tengas MÁS certeza que el mercado. Aplica el razonamiento de 3 pasos completo.

🛡️ PICK MÁS SEGURO:
El resultado con MAYOR probabilidad de ocurrir de todos los disponibles. Prioriza certeza sobre rentabilidad. Elige el mercado más predecible y respaldado por datos reales (puede ser Over/Under, Doble Oportunidad, etc.). No importa si la cuota es 1.10, lo que importa es que casi seguramente ocurra.

══════════════════════════════════════════════════════════════
MERCADOS DISPONIBLES PARA TUS PICKS
══════════════════════════════════════════════════════════════
Usa cualquiera de: Ganador 1X2 | Doble Oportunidad (1X / X2 / 12) | Over/Under Goles (elige el punto más eficiente del mercado) | Ambos Equipos Anotan (Sí/No) | Hándicap Asiático (si está disponible en los datos).

══════════════════════════════════════════════════════════════
REGLAS DE CUOTAS POR ESTRATEGIA
══════════════════════════════════════════════════════════════
🛡️ Estrategia Segura:     Cuota total final @1.15 – @1.40  |  1 a 2 picks
⚖️ Estrategia Moderada:   Cuota total final @2.35 – @4.20  |  2 a 4 picks
🔥 Estrategia Arriesgada: Cuota total final @4.25 – @8.95  |  3 a 7 picks

══════════════════════════════════════════════════════════════
FORMATO DE RESPUESTA — JSON EXACTO
══════════════════════════════════════════════════════════════
Responde ÚNICAMENTE con este JSON (sin bloques ```json, sin texto previo ni posterior):

{{
  "game_script": "Análisis táctico y contextual de los partidos seleccionados. Qué esperar basándote en los datos reales de forma, posición y goles.",

  "pick_estrella": {{
    "partido": "Local vs Visita",
    "seleccion": "El mercado con mayor valor esperado del día",
    "cuota": "X.XX",
    "nivel_confianza": "Alta",
    "razonamiento": "PASO 1 [Diagnóstico]: [análisis forma/posición/contexto del partido]. PASO 2 [Mercado]: [probabilidad implícita vs real, ¿hay +EV?]. PASO 3 [Veredicto]: [por qué ocurrirá y cuál es el riesgo real]."
  }},

  "pick_mas_seguro": {{
    "partido": "Local vs Visita",
    "seleccion": "El resultado más predecible y probable de ocurrir",
    "cuota": "X.XX",
    "probabilidad_estimada": "XX%",
    "razonamiento": "Por qué este es el resultado más seguro según los datos. Qué factores lo hacen casi inevitable."
  }},

  "estrategias": [
    {{
      "nivel": "🛡️ La Apuesta Segura (Protección de Bankroll)",
      "picks": [
        {{
          "partido": "Local vs Visita",
          "seleccion": "Mercado elegido",
          "cuota": "X.XX",
          "razonamiento_pick": "PASO 1 [Diagnóstico]: ... PASO 2 [Mercado]: ... PASO 3 [Veredicto]: ..."
        }}
      ],
      "cuota_total": "X.XX",
      "justificacion": "Por qué esta combinación es sólida y tiene alta probabilidad de éxito."
    }},
    {{
      "nivel": "⚖️ La Apuesta Moderada (+EV Balanceado)",
      "picks": [
        {{
          "partido": "Local vs Visita",
          "seleccion": "Mercado",
          "cuota": "X.XX",
          "razonamiento_pick": "PASO 1 [Diagnóstico]: ... PASO 2 [Mercado]: ... PASO 3 [Veredicto]: ..."
        }}
      ],
      "cuota_total": "X.XX",
      "justificacion": "Equilibrio entre valor esperado y probabilidad de acertar."
    }},
    {{
      "nivel": "🔥 La Apuesta Arriesgada (Ineficiencia de Mercado)",
      "picks": [
        {{
          "partido": "Local vs Visita",
          "seleccion": "Mercado",
          "cuota": "X.XX",
          "razonamiento_pick": "PASO 1 [Diagnóstico]: ... PASO 2 [Mercado]: ... PASO 3 [Veredicto]: ..."
        }}
      ],
      "cuota_total": "X.XX",
      "justificacion": "Ineficiencia detectada en el mercado y potencial de ganancia multiplicada."
    }}
  ]
}}
"""

        data = None
        origen_datos = "📥 Análisis generado exitosamente (Sistema de Súper Caché Activo)"
        
        with st.spinner("🧠 El algoritmo está razonando pick a pick..."):
            try:
                data = obtener_analisis_ia(api_gemini_ss, prompt, id_combinacion)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower() or "exhausted" in error_msg.lower():
                    st.warning("⏳ Has alcanzado el límite de consultas rápidas de la IA. Por favor, espera 1 minuto exacto.")
                elif "503" in error_msg or "high demand" in error_msg.lower():
                    st.warning("⏳ Los servidores de Google están experimentando mucha demanda. Por favor, espera unos segundos.")
                else:
                    st.error(f"❌ Error al procesar respuesta de la IA. Detalle: {e}")

        # ── RENDERIZADO DEL RESULTADO ────────────────────────────────────
        if data:
            st.markdown("### 📈 El Veredicto del Algoritmo")
            st.caption(f"ℹ️ *{origen_datos}*")

            # Game Script
            st.markdown(f"""
            <div style="background:#0d1117;border-left:4px solid #8b5cf6;padding:14px 16px;border-radius:8px;margin-bottom:20px;">
                <div style="color:#a78bfa;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">⚡ Game Script (Contexto Deducido)</div>
                <div style="font-size:14px;color:#e1e1e1;line-height:1.5;"><i>"{data.get('game_script', '')}"</i></div>
            </div>
            """, unsafe_allow_html=True)

            # ── PICKS DESTACADOS: ESTRELLA + MÁS SEGURO ─────────────────
            pick_e = data.get('pick_estrella', {})
            pick_s = data.get('pick_mas_seguro', {})

            if pick_e or pick_s:
                st.markdown("""
                <div style="color:#e1e1e1;font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
                  <span style="display:inline-block;width:28px;height:2px;background:linear-gradient(90deg,#f59e0b,transparent);border-radius:2px;"></span>
                  PICKS DESTACADOS DEL DÍA
                  <span style="display:inline-block;flex:1;height:2px;background:linear-gradient(90deg,transparent,#f59e0b20);border-radius:2px;"></span>
                </div>
                """, unsafe_allow_html=True)
                
                col_e, col_s = st.columns(2)

                with col_e:
                    if pick_e:
                        confianza = pick_e.get('nivel_confianza', 'Alta')
                        confianza_color = "#22c55e" if confianza == 'Alta' else "#f59e0b" if confianza == 'Media' else "#ef4444"
                        st.markdown(f"""
                        <div style="background:linear-gradient(145deg,#1c1400,#0d1117);border:2px solid #f59e0b;border-radius:14px;padding:16px;min-height:170px;box-shadow:0 0 20px rgba(245,158,11,0.12);">
                            <div style="color:#f59e0b;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;">⭐ PICK ESTRELLA</div>
                            <div style="color:#fef3c7;font-size:11px;font-weight:700;margin-bottom:3px;opacity:0.8;">{pick_e.get('partido','')}</div>
                            <div style="color:#ffffff;font-size:14px;font-weight:800;margin-bottom:14px;line-height:1.3;">{pick_e.get('seleccion','')}</div>
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <span style="background:#f59e0b;color:#0d1117;padding:6px 14px;border-radius:8px;font-weight:900;font-size:18px;">@{pick_e.get('cuota','')}</span>
                                <span style="border:1px solid {confianza_color};color:{confianza_color};padding:4px 9px;border-radius:10px;font-size:10px;font-weight:800;">🎯 {confianza}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                with col_s:
                    if pick_s:
                        prob = pick_s.get('probabilidad_estimada', '?%')
                        st.markdown(f"""
                        <div style="background:linear-gradient(145deg,#001a0d,#0d1117);border:2px solid #22c55e;border-radius:14px;padding:16px;min-height:170px;box-shadow:0 0 20px rgba(34,197,94,0.12);">
                            <div style="color:#22c55e;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;">🛡️ MÁS SEGURO</div>
                            <div style="color:#dcfce7;font-size:11px;font-weight:700;margin-bottom:3px;opacity:0.8;">{pick_s.get('partido','')}</div>
                            <div style="color:#ffffff;font-size:14px;font-weight:800;margin-bottom:14px;line-height:1.3;">{pick_s.get('seleccion','')}</div>
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <span style="background:#22c55e;color:#0d1117;padding:6px 14px;border-radius:8px;font-weight:900;font-size:18px;">@{pick_s.get('cuota','')}</span>
                                <span style="border:1px solid #22c55e;color:#22c55e;padding:4px 9px;border-radius:10px;font-size:10px;font-weight:800;">📊 {prob}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                # Razonamiento de los picks destacados (expandible)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                col_re, col_rs = st.columns(2)

                with col_re:
                    if pick_e.get('razonamiento'):
                        with st.expander("🧠 Ver análisis del Pick Estrella"):
                            razon = pick_e['razonamiento']
                            razon_fmt = (razon
                                .replace('PASO 1', '<b style="color:#f59e0b">🔍 PASO 1</b>')
                                .replace('PASO 2', '<b style="color:#f59e0b">📊 PASO 2</b>')
                                .replace('PASO 3', '<b style="color:#f59e0b">✅ PASO 3</b>')
                                .replace('[Diagnóstico]', '<span style="color:#a78bfa">[Diagnóstico]</span>')
                                .replace('[Mercado]', '<span style="color:#a78bfa">[Mercado]</span>')
                                .replace('[Veredicto]', '<span style="color:#a78bfa">[Veredicto]</span>')
                            )
                            st.markdown(f"""<div style="background:#1c1400;padding:13px;border-radius:8px;color:#cbd5e1;font-size:12px;line-height:1.65;border:1px solid #f59e0b30;">{razon_fmt}</div>""", unsafe_allow_html=True)

                with col_rs:
                    if pick_s.get('razonamiento'):
                        with st.expander("🧠 Ver análisis del Pick Más Seguro"):
                            st.markdown(f"""<div style="background:#001a0d;padding:13px;border-radius:8px;color:#cbd5e1;font-size:12px;line-height:1.65;border:1px solid #22c55e30;">{pick_s['razonamiento']}</div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div style="color:#8b949e;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;">📊 ESTRATEGIAS POR NIVEL DE RIESGO</div>
            """, unsafe_allow_html=True)

            # ── ESTRATEGIAS CON RAZONAMIENTO POR PICK ───────────────────
            tabs = st.tabs(["🛡️ Segura", "⚖️ Moderada", "🔥 Arriesgada"])

            for i, tab in enumerate(tabs):
                with tab:
                    est = data['estrategias'][i]
                    picks_html = ""

                    for pick in est['picks']:
                        razonamiento = pick.get('razonamiento_pick', '')
                        raz_block = ""

                        if razonamiento:
                            raz_fmt = (razonamiento
                                .replace('PASO 1', '<b style="color:#818cf8">🔍 PASO 1</b>')
                                .replace('PASO 2', '<b style="color:#818cf8">📊 PASO 2</b>')
                                .replace('PASO 3', '<b style="color:#818cf8">✅ PASO 3</b>')
                                .replace('[Diagnóstico]', '<span style="color:#94a3b8">[Diagnóstico]</span>')
                                .replace('[Mercado]', '<span style="color:#94a3b8">[Mercado]</span>')
                                .replace('[Veredicto]', '<span style="color:#94a3b8">[Veredicto]</span>')
                            )
                            raz_block = f"""
<div style="background:#0a0f1e;padding:10px 12px;border-radius:6px;border-left:3px solid #8b5cf6;margin-top:9px;">
  <div style="color:#a78bfa;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:5px;">🧠 Razonamiento del algoritmo</div>
  <p style="color:#94a3b8;font-size:12px;line-height:1.6;margin:0;">{raz_fmt}</p>
</div>"""

                        picks_html += f"""
<div style="background:#0f172a;padding:13px;border-radius:10px;margin-bottom:10px;border:1px solid #1e293b;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;flex-direction:column;flex:1;padding-right:10px;">
      <span style="color:#8b949e;font-size:11px;font-weight:700;margin-bottom:3px;">⚽ {pick['partido']}</span>
      <span style="color:#e1e1e1;font-size:14px;font-weight:700;">{pick['seleccion']}</span>
    </div>
    <span style="background:#10b981;color:#0f172a;padding:5px 12px;border-radius:7px;font-weight:900;font-size:14px;white-space:nowrap;">@{pick['cuota']}</span>
  </div>
  {raz_block}
</div>"""

                    st.markdown(f"""
<div style="background:#161c2b;border:2px dashed #2d3748;border-radius:12px;padding:16px;margin-top:8px;">
  <h4 style="color:#f8fafc;margin-top:0;border-bottom:1px solid #2d3748;padding-bottom:10px;margin-bottom:16px;">{est['nivel']}</h4>
  {picks_html}
  <div style="display:flex;justify-content:flex-end;margin-top:16px;margin-bottom:16px;">
    <div style="background:#8b5cf615;border:1px solid #8b5cf6;padding:8px 16px;border-radius:8px;">
      <span style="color:#c4b5fd;font-size:12px;font-weight:700;">CUOTA TOTAL APROX:</span>
      <span style="color:#a78bfa;font-size:18px;font-weight:900;margin-left:8px;">@{est['cuota_total']}</span>
    </div>
  </div>
  <div style="background:#1e293b;padding:12px;border-radius:8px;border-left:3px solid #f59e0b;">
    <span style="color:#fcd34d;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">Tesis Cuantitativa (+EV)</span>
    <p style="color:#cbd5e1;font-size:13px;line-height:1.5;margin-top:6px;margin-bottom:0;">{est['justificacion']}</p>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
