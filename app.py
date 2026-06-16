"""
app.py — BET⚡COMBINADAS
Dashboard principal del sistema de predicción de apuestas deportivas.
Integra: Football-Data.org + Odds API + Dixon-Coles + Gemini IA
"""

from typing import List, Tuple
import streamlit as st
import requests
import re
import json
from datetime import datetime, timezone, timedelta, date
from collections import defaultdict
from google import genai
from google.genai import types

import bd
import datos as datos_mod
import modelo as modelo_mod
import gemini as gemini_mod
import elo as elo_mod

try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-4))

def compact(s):
    return re.sub(r'\n\s*', '', str(s))

PAISES_ES = {
    "Germany":"Alemania","France":"Francia","Spain":"España","Italy":"Italia",
    "Brazil":"Brasil","Argentina":"Argentina","England":"Inglaterra",
    "Portugal":"Portugal","Netherlands":"Países Bajos","Belgium":"Bélgica",
    "Croatia":"Croacia","Uruguay":"Uruguay","Mexico":"México",
    "United States":"EE.UU.","USA":"EE.UU.","Japan":"Japón",
    "South Korea":"Corea del Sur","Australia":"Australia","Senegal":"Senegal",
    "Morocco":"Marruecos","Tunisia":"Túnez","Cameroon":"Camerún",
    "Ghana":"Ghana","Nigeria":"Nigeria","Ivory Coast":"Costa de Marfil",
    "Egypt":"Egipto","Saudi Arabia":"Arabia Saudita","Iran":"Irán",
    "Qatar":"Catar","Switzerland":"Suiza","Poland":"Polonia",
    "Denmark":"Dinamarca","Sweden":"Suecia","Norway":"Noruega",
    "Finland":"Finlandia","Ecuador":"Ecuador","Colombia":"Colombia",
    "Peru":"Perú","Chile":"Chile","Paraguay":"Paraguay","Bolivia":"Bolivia",
    "Venezuela":"Venezuela","Turkey":"Türkiye","Serbia":"Serbia",
    "Ukraine":"Ucrania","Austria":"Austria","Wales":"Gales","Scotland":"Escocia",
    "Canada":"Canadá","Costa Rica":"Costa Rica","Panama":"Panamá",
    "Honduras":"Honduras","Jamaica":"Jamaica","New Zealand":"Nueva Zelanda",
    "Curaçao":"Curazao","Cape Verde":"Cabo Verde","Algeria":"Argelia",
    "Draw":"Empate",
}
FLAGS = {
    "Germany":"🇩🇪","France":"🇫🇷","Spain":"🇪🇸","Italy":"🇮🇹",
    "Brazil":"🇧🇷","Argentina":"🇦🇷","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Portugal":"🇵🇹",
    "Netherlands":"🇳🇱","Belgium":"🇧🇪","Croatia":"🇭🇷","Uruguay":"🇺🇾",
    "Mexico":"🇲🇽","United States":"🇺🇸","USA":"🇺🇸","Japan":"🇯🇵",
    "South Korea":"🇰🇷","Australia":"🇦🇺","Senegal":"🇸🇳","Morocco":"🇲🇦",
    "Tunisia":"🇹🇳","Cameroon":"🇨🇲","Ghana":"🇬🇭","Nigeria":"🇳🇬",
    "Ivory Coast":"🇨🇮","Egypt":"🇪🇬","Saudi Arabia":"🇸🇦","Iran":"🇮🇷",
    "Qatar":"🇶🇦","Switzerland":"🇨🇭","Poland":"🇵🇱","Denmark":"🇩🇰",
    "Sweden":"🇸🇪","Norway":"🇳🇴","Finland":"🇫🇮","Ecuador":"🇪🇨",
    "Colombia":"🇨🇴","Peru":"🇵🇪","Chile":"🇨🇱","Paraguay":"🇵🇾",
    "Bolivia":"🇧🇴","Venezuela":"🇻🇪","Turkey":"🇹🇷","Serbia":"🇷🇸",
    "Ukraine":"🇺🇦","Austria":"🇦🇹","Wales":"🏴󠁧󠁢󠁷󠁬󠁳󠁿","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Canada":"🇨🇦","Costa Rica":"🇨🇷","Panama":"🇵🇦","Honduras":"🇭🇳",
    "Jamaica":"🇯🇲","New Zealand":"🇳🇿","Curaçao":"🇨🇼","Cape Verde":"🇨🇻",
    "Algeria":"🇩🇿",
}
DIAS_ES  = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
            "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
MESES_ES = {"Jan":"Ene","Feb":"Feb","Mar":"Mar","Apr":"Abr","May":"May","Jun":"Jun",
            "Jul":"Jul","Aug":"Ago","Sep":"Sep","Oct":"Oct","Nov":"Nov","Dec":"Dic"}

def tr(n):  return PAISES_ES.get(n, n)
def fl(n):  return FLAGS.get(n, "🌍")
def tr_pick(t):
    for en, es in sorted(PAISES_ES.items(), key=lambda x: -len(x[0])):
        t = t.replace(en, es)
    return t
def fmt_grupo(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(TZ_CHILE)
        return f"{DIAS_ES.get(dt.strftime('%A'),dt.strftime('%A'))} {dt.day} {MESES_ES.get(dt.strftime('%b'),dt.strftime('%b'))}"
    except: return "Próximamente"
def fmt_hora(iso):
    try: return datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(TZ_CHILE).strftime("%H:%M")
    except: return "N/D"
def fmt_fecha(iso):
    try: return datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(TZ_CHILE).strftime("%d %b %H:%M")
    except: return "N/D"

COMPETICIONES = {
    "🏆 Copa del Mundo 2026": ("FIFA World Cup", "2026", "soccer_fifa_world_cup"),
    "⚽ Premier League":      ("Premier League", "2025", "soccer_epl"),
    "🇪🇸 La Liga":           ("La Liga",        "2025", "soccer_spain_la_liga"),
    "🇮🇹 Serie A":           ("Serie A",        "2025", "soccer_italy_serie_a"),
    "🇩🇪 Bundesliga":        ("Bundesliga",     "2025", "soccer_germany_bundesliga"),
    "🇫🇷 Ligue 1":           ("Ligue 1",        "2025", "soccer_france_ligue_one"),
}

st.set_page_config(page_title="BET⚡COMBINADAS", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
[data-testid="stAppViewContainer"]{background:#07101E!important;color:#EEF4FF!important;font-family:'Inter',sans-serif!important;}
[data-testid="stHeader"]{background:transparent!important;}
.block-container{padding-top:1rem!important;max-width:680px!important;}
.hdr{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;background:linear-gradient(135deg,#0D1B2E,#0E2040);border:1px solid rgba(0,194,255,.12);border-radius:16px;margin-bottom:22px;box-shadow:0 4px 30px rgba(0,0,0,.4);}
.logo{font-size:22px;font-weight:900;letter-spacing:-1px;color:#fff;}
.logo-bolt{color:#00C2FF;text-shadow:0 0 20px rgba(0,194,255,.6);}
.badge{background:rgba(255,107,0,.15);border:1px solid rgba(255,107,0,.35);padding:5px 13px;border-radius:20px;font-size:10px;font-weight:800;color:#FF6B00;text-transform:uppercase;letter-spacing:.5px;}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:#0A1525!important;border-radius:10px!important;padding:4px!important;gap:4px!important;}
[data-testid="stTabs"] button{border-radius:8px!important;font-weight:700!important;font-size:12px!important;color:#8A97B5!important;}
[data-testid="stTabs"] button[aria-selected="true"]{background:#0E1A2C!important;color:#00C2FF!important;box-shadow:0 2px 8px rgba(0,0,0,.3)!important;}
.stButton>button{background:linear-gradient(135deg,#00C2FF,#0080CC)!important;border:none!important;border-radius:10px!important;color:#fff!important;font-weight:800!important;font-size:14px!important;width:100%!important;padding:.85em!important;transition:all .2s!important;box-shadow:0 4px 15px rgba(0,194,255,.2)!important;}
.stButton>button:hover{opacity:.92!important;transform:translateY(-1px)!important;}
.btn-save>button{background:linear-gradient(135deg,#8B5CF6,#6D28D9)!important;}
.date-sep{display:flex;align-items:center;gap:10px;margin:28px 0 14px;}
.date-badge{background:rgba(0,194,255,.08);border:1px solid rgba(0,194,255,.2);color:#00C2FF;font-size:10px;font-weight:800;padding:5px 14px;border-radius:20px;text-transform:uppercase;letter-spacing:.8px;white-space:nowrap;}
.date-cnt{background:rgba(255,255,255,.06);color:#8A97B5;font-size:10px;font-weight:700;padding:4px 10px;border-radius:10px;}
.date-line{flex:1;height:1px;background:linear-gradient(90deg,rgba(0,194,255,.15),transparent);}
.mcard{background:linear-gradient(145deg,#0D1B2E,#0B1725);border:1px solid rgba(255,255,255,.08);border-bottom:none;border-radius:16px 16px 0 0;padding:18px 20px 16px;margin-bottom:0;}
.teams-row{display:grid;grid-template-columns:1fr 88px 1fr;align-items:center;gap:8px;margin-bottom:16px;}
.team-blk{display:flex;flex-direction:column;align-items:center;gap:5px;}
.t-flag{font-size:38px;line-height:1;}
.t-name{font-size:12px;font-weight:800;color:#EEF4FF;text-align:center;line-height:1.2;}
.t-cuota{font-size:10px;color:#8B5CF6;font-weight:700;background:rgba(139,92,246,.1);padding:2px 7px;border-radius:6px;}
.center-blk{display:flex;flex-direction:column;align-items:center;gap:3px;}
.mc-time{font-size:22px;font-weight:900;color:#00C2FF;letter-spacing:-1.5px;text-shadow:0 0 20px rgba(0,194,255,.4);}
.mc-vs{font-size:9px;font-weight:800;color:#2A3C52;letter-spacing:2.5px;text-transform:uppercase;}
.mc-draw{font-size:10px;color:#8A97B5;font-weight:700;background:rgba(255,255,255,.05);padding:2px 7px;border-radius:6px;}
.prob-wrap{margin-top:4px;}
.prob-labels{display:flex;justify-content:space-between;font-size:9px;color:#8A97B5;font-weight:700;margin-bottom:6px;text-transform:uppercase;}
.prob-bar{display:flex;height:7px;border-radius:4px;overflow:hidden;gap:2px;}
.pb-h{background:linear-gradient(90deg,#00C2FF,#0099D9);border-radius:4px 0 0 4px;}
.pb-d{background:#7C4DFF;}
.pb-a{background:linear-gradient(90deg,#FF6B6B,#FF3B5C);border-radius:0 4px 4px 0;}
.prob-pcts{display:flex;justify-content:space-between;font-size:11px;font-weight:800;margin-top:6px;}
.pct-h{color:#00C2FF;}.pct-d{color:#9B71FF;}.pct-a{color:#FF6B6B;}
.mcard-footer{background:#091420;border:1px solid rgba(255,255,255,.08);border-top:1px dashed rgba(0,194,255,.1);border-radius:0 0 16px 16px;padding:6px 20px;margin-bottom:16px;}
.mcard-footer [data-testid="stCheckbox"]{background:transparent!important;border:none!important;padding:4px 0!important;margin:0!important;}
.mcard-footer label p{font-size:11px!important;font-weight:700!important;color:#8A97B5!important;text-transform:uppercase!important;letter-spacing:.6px!important;}
.tslip{background:linear-gradient(145deg,#101C2E,#0D1828);border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:18px 20px;margin-bottom:16px;position:relative;overflow:hidden;}
.tslip::before{content:'';position:absolute;top:0;left:0;width:5px;height:100%;}
.slip-base::before{background:linear-gradient(180deg,#00C2FF,#0080CC);}
.slip-anti::before{background:linear-gradient(180deg,#8B5CF6,#6D28D9);}
.slip-segura::before{background:linear-gradient(180deg,#00E676,#00A854);}
.slip-moderada::before{background:linear-gradient(180deg,#FFB700,#E6A000);}
.slip-arriesgada::before{background:linear-gradient(180deg,#FF3B5C,#CC1F3D);}
.slip-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,.05);padding-bottom:11px;}
.slip-tit{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:#EEF4FF;}
.slip-q{background:rgba(255,107,0,.15);color:#FF6B00;padding:4px 11px;border-radius:7px;font-weight:800;font-size:14px;border:1px solid rgba(255,107,0,.3);}
.i-match{font-size:10px;font-weight:700;color:#8A97B5;margin-top:9px;text-transform:uppercase;letter-spacing:.5px;}
.i-bet{font-size:15px;color:#EEF4FF;font-weight:800;padding-left:22px;margin-bottom:6px;position:relative;}
.i-bet::before{content:'🎯';position:absolute;left:0;top:2px;font-size:12px;}
.slip-desc{font-size:11px;color:#8A97B5;line-height:1.6;margin-top:12px;padding-top:10px;border-top:1px dashed rgba(255,255,255,.07);}
.pred-card{background:linear-gradient(145deg,#0D1B2E,#0B1725);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 18px;margin-bottom:12px;}
.pred-teams{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}
.pred-team{font-size:13px;font-weight:800;color:#EEF4FF;}
.pred-time{font-size:11px;color:#00C2FF;font-weight:700;}
.ev-badge{display:inline-block;background:rgba(0,230,118,.15);border:1px solid rgba(0,230,118,.3);color:#00E676;font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;margin:2px;}
.ev-badge-mod{background:rgba(255,183,0,.15);border-color:rgba(255,183,0,.3);color:#FFB700;}
.dash-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px;}
.d-card{background:linear-gradient(145deg,#0D1B2E,#0B1725);border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:16px;text-align:center;}
.d-val{font-size:26px;font-weight:900;color:#fff;margin-bottom:4px;letter-spacing:-1px;}
.d-lbl{font-size:10px;font-weight:700;color:#8A97B5;text-transform:uppercase;letter-spacing:.5px;}
.hist-row{display:flex;justify-content:space-between;align-items:center;background:#0E1A2C;padding:12px 14px;border-radius:9px;margin-bottom:8px;border-left:3px solid #4A5568;}
.h-meta{font-size:12px;color:#EEF4FF;font-weight:800;margin-bottom:2px;}
.h-txt{font-size:11px;color:#8A97B5;}
.h-badge{font-size:10px;font-weight:800;text-transform:uppercase;padding:3px 9px;border-radius:5px;letter-spacing:.5px;}
.sys-card{background:#0E1A2C;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:16px 18px;margin-bottom:12px;}
.sys-title{font-size:12px;font-weight:800;color:#8A97B5;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px;}
</style>
<div class="hdr">
  <div class="logo">BET<span class="logo-bolt">⚡</span>COMBINADAS</div>
  <div class="badge">🎯 MUNDIAL & LIGAS · IA CUÁNTICA</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# CREDENCIALES
# ═══════════════════════════════════════════════════════════════
api_gemini   = st.secrets.get("GEMINI_API", "")
api_odds     = st.secrets.get("ODDS_API", "")
supa_url     = st.secrets.get("SUPABASE_URL", "")
supa_key     = st.secrets.get("SUPABASE_KEY", "")
api_football = st.secrets.get("FOOTBALL_API", "")

if not all([api_gemini, api_odds, supa_url, supa_key, api_football]):
    st.warning("⚠️ Faltan credenciales. Verifica en Secrets: GEMINI_API, ODDS_API, SUPABASE_URL, SUPABASE_KEY, FOOTBALL_API.")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# FUNCIONES COMPARTIDAS
# ═══════════════════════════════════════════════════════════════
# ── Bookmakers en orden de prioridad (Betano primero) ──────────
BM_PRIORITY = ["betano", "pinnacle", "bet365", "unibet", "bwin", "williamhill"]

def extraer_h2h(partido):
    """Extrae cuotas H2H priorizando Betano > Pinnacle > otros bookmakers."""
    home, away = partido.get("home_team",""), partido.get("away_team","")

    def prioridad_bm(bm):
        key = bm.get("key","").lower()
        for i, pref in enumerate(BM_PRIORITY):
            if pref in key: return i
        return len(BM_PRIORITY)

    bookmakers = sorted(partido.get("bookmakers",[]), key=prioridad_bm)

    for bm in bookmakers:
        for mkt in bm.get("markets",[]):
            if mkt.get("key")=="h2h":
                cuotas = {o["name"]:o["price"] for o in mkt.get("outcomes",[])}
                ho,do,ao = cuotas.get(home,0),cuotas.get("Draw",0),cuotas.get(away,0)
                if ho and ao:
                    ph,pd,pa = 1/ho,(1/do if do else 0),1/ao
                    t = ph+pd+pa
                    return {
                        "home":round(ph/t*100),"draw":round(pd/t*100) if do else 0,
                        "away":round(pa/t*100),"home_odd":ho,"draw_odd":do,"away_odd":ao,
                        "bookmaker": bm.get("title",""),
                    }
    return None

# ── Validador de Reglas de Oro (código, no solo prompt) ────────
MERCADOS_1X2       = {"1x2","ganador","victoria","resultado final"}
MERCADOS_HANDICAP  = {"hándicap","handicap","asian handicap","hcap"}
MERCADOS_GOALS     = {"over","under","goles","total"}
MERCADOS_CORNERS   = {"corner","córner","esquina"}
MERCADOS_TARJETAS  = {"tarjeta","card","yellow","roja"}

def categorizar_mercado(mercado_str: str) -> str:
    m = mercado_str.lower()
    if any(k in m for k in MERCADOS_1X2):      return "1x2"
    if any(k in m for k in MERCADOS_HANDICAP): return "handicap"
    if any(k in m for k in MERCADOS_GOALS):    return "goles"
    if any(k in m for k in MERCADOS_CORNERS):  return "corners"
    if any(k in m for k in MERCADOS_TARJETAS): return "tarjetas"
    return "otro"

def extraer_partido_de_pick(pick_str: str) -> str:
    """Extrae el nombre del partido de un string de pick."""
    if ":" in pick_str:
        return pick_str.split(":")[0].strip().lower()
    return pick_str.lower()[:30]

def validar_combinada(picks: List) -> Tuple[List, List]:
    """
    Valida que la combinada respete las Reglas de Oro:
    1. No mezclar 1X2 y Hándicap del MISMO partido.
    2. Cuotas dentro de rangos razonables.
    Retorna (picks_validos, advertencias).
    """
    from typing import List, Tuple
    advertencias = []
    picks_validos = []
    partidos_1x2      = {}  # partido → pick
    partidos_handicap = {}

    for pick in picks:
        pick_str = str(pick)
        partido  = extraer_partido_de_pick(pick_str)
        cat      = categorizar_mercado(pick_str)

        if cat == "1x2":
            if partido in partidos_handicap:
                advertencias.append(f"⚠️ Regla 2 violada: '{partido[:30]}' tiene 1X2 y Hándicap. Se eliminó el hándicap.")
                picks_validos = [p for p in picks_validos if extraer_partido_de_pick(str(p)) != partido]
                partidos_handicap.pop(partido)
            partidos_1x2[partido] = pick

        elif cat == "handicap":
            if partido in partidos_1x2:
                advertencias.append(f"⚠️ Regla 2 violada: '{partido[:30]}' ya tiene 1X2. Hándicap ignorado.")
                continue
            partidos_handicap[partido] = pick

        picks_validos.append(pick)

    return picks_validos, advertencias

def extraer_cuotas_odds(partido_odds):
    cuotas = {}
    home = partido_odds.get("home_team","")
    away = partido_odds.get("away_team","")
    for bm in partido_odds.get("bookmakers",[]):
        for mkt in bm.get("markets",[]):
            key      = mkt.get("key","")
            outcomes = mkt.get("outcomes",[])
            if key == "h2h":
                for o in outcomes:
                    if o["name"] == home:     cuotas["home"] = o["price"]
                    elif o["name"]=="Draw":   cuotas["draw"] = o["price"]
                    elif o["name"] == away:   cuotas["away"] = o["price"]
            elif key == "totals":
                for o in outcomes:
                    pt = str(o.get("point",""))
                    if "Over"  in o["name"] and pt=="2.5": cuotas["over25"]  = o["price"]
                    if "Under" in o["name"] and pt=="2.5": cuotas["under25"] = o["price"]
                    if "Over"  in o["name"] and pt=="1.5": cuotas["over15"]  = o["price"]
                    if "Under" in o["name"] and pt=="1.5": cuotas["under15"] = o["price"]
        break
    return cuotas

def emparejar_partido(home_fd, away_fd, lista_odds):
    def limpiar(n): return re.sub(r'\bfc\b|\bsc\b|\bac\b','',n.lower()).strip()
    h = limpiar(home_fd); a = limpiar(away_fd)
    for p in lista_odds:
        ho = limpiar(p.get("home_team","")); ao = limpiar(p.get("away_team",""))
        if (h[:5] in ho or ho[:5] in h) and (a[:5] in ao or ao[:5] in a):
            return extraer_cuotas_odds(p)
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_odds_competicion(sport_key):
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/",
            params={"apiKey":api_odds,"regions":"eu,uk","markets":"h2h,totals"},
            timeout=10)
        r.raise_for_status(); return r.json()
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_partidos_mundial():
    try:
        r = requests.get(
            "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/",
            params={"apiKey":api_odds,"regions":"eu,uk,us","markets":"h2h,totals,spreads"},
            timeout=10)
        r.raise_for_status(); return r.json()
    except Exception as e: return {"error": str(e)}

@st.cache_data(ttl=86400, show_spinner=False)
def ejecutar_algoritmo_quant(partidos_seleccionados):
    prompt = """Eres un Analista Cuantitativo de Apuestas del Mundial FIFA 2026. Genera picks con máxima probabilidad de acierto.

REGLA DE ORO 1 — FILOSOFÍA:
Solo picks con probabilidad real >65%. Cuotas objetivo @1.15-@1.45.
Prefiere: Doble Oportunidad, Over 1.5, Over 2.5 en partidos entre equipos atacantes.

REGLA DE ORO 2 — ANTI-CORRELACIÓN (CRÍTICO — BETANO LO PROHÍBE):
NUNCA en la misma combinada: Ganador 1X2 + Hándicap del MISMO partido.
CORRECTO: "Alemania gana (1X2)" + "Alemania Over 2.5 goles" → mercados distintos, OK
INCORRECTO: "Alemania gana (1X2)" + "Alemania -1.5 hándicap" → MISMO resultado, PROHIBIDO

REGLA DE ORO 3 — INDEPENDENCIA:
Los picks de una combinada deben ser de partidos DISTINTOS o de mercados INDEPENDIENTES.

MERCADOS PERMITIDOS EN BETANO:
✅ Ganador del partido (1, X, 2)
✅ Doble Oportunidad (1X, X2, 12)
✅ Total de Goles Over/Under (0.5, 1.5, 2.5, 3.5, 4.5)
✅ Ambos Equipos Marcan (Sí/No)
✅ Córners Over/Under
✅ Tarjetas Over/Under
✅ Hándicap (NUNCA con 1X2 del mismo partido)

ESTRUCTURA DE BOLETOS:
- SEGURA: 1-2 picks, cuota total @1.15-@1.50. Máxima certeza.
- MODERADA: 2-3 picks, cuota total @1.50-@3.50. Balance riesgo/retorno.
- ARRIESGADA: 3-4 picks, cuota total @3.50-@7.00. Mayor potencial.

PARTIDOS DISPONIBLES:
""" + json.dumps(partidos_seleccionados, ensure_ascii=False) + """

Responde SOLO con JSON válido (sin markdown, sin texto extra):
{"game_script":"análisis de las mejores oportunidades en 2 oraciones","pick_estrella":{"partido":"Equipo A vs Equipo B","categoria_permitida":"Over/Under","seleccion":"Over 1.5","cuota_betano":1.25,"razon_cuantitativa":"justificación basada en datos"},"pick_mas_seguro":{"partido":"Equipo C vs Equipo D","categoria_permitida":"Doble Oportunidad","seleccion":"1X","cuota_betano":1.18,"razon_cuantitativa":"justificación"},"estrategias":[{"tipo":"segura","cuota_total":1.35,"descripcion":"estrategia conservadora","picks":["Partido A: Over 1.5 (@1.25)","Partido B: 1X (@1.08)"]},{"tipo":"moderada","cuota_total":2.20,"descripcion":"balance óptimo","picks":["Partido A: Pick1 (@1.25)","Partido B: Pick2 (@1.30)","Partido C: Pick3 (@1.35)"]},{"tipo":"arriesgada","cuota_total":4.50,"descripcion":"máximo retorno","picks":["Partido A: Pick1 (@1.30)","Partido B: Pick2 (@1.40)","Partido C: Pick3 (@1.35)","Partido D: Pick4 (@1.25)"]}]}"""

    try:
        client = genai.Client(api_key=api_gemini)
        resp   = client.models.generate_content(
            model="gemini-3.1-flash-lite", contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=4096, temperature=0.1,
                response_mime_type="application/json"))
        data = json.loads(resp.text.strip().replace("```json","").replace("```","").strip())

        # ── Validar Reglas de Oro en código ──────────────────────
        for estrategia in data.get("estrategias", []):
            picks_orig = estrategia.get("picks", [])
            picks_ok, avisos = validar_combinada(picks_orig)
            estrategia["picks"] = picks_ok
            if avisos:
                estrategia["advertencias"] = avisos

        return data
    except Exception as e:
        return {"error": str(e)}

def auto_verificar_jornada():
    try:
        pendientes = bd.get_client().table("historial").select("*").or_(
            "res_estrella.eq.pendiente,res_mas_seguro.eq.pendiente,res_segura.eq.pendiente,res_moderada.eq.pendiente,res_arriesgada.eq.pendiente"
        ).execute().data
        if not pendientes: return
        r = requests.get(f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/scores/?apiKey={api_odds}&daysFrom=3", timeout=10)
        if r.status_code != 200: return
        picks_pend = bd.get_valores_pendientes("FIFA World Cup")
        if picks_pend:
            resultados = gemini_mod.verificar_picks_pendientes(picks_pend)
            for r2 in resultados:
                if r2.get("pick_resultado") in ("acertado","fallido"):
                    bd.actualizar_resultado_valor(r2["id"], r2["pick_resultado"])
    except: pass

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Boletos IA", "🔮 Predicciones", "📊 Estadísticas", "⚙️ Sistema"])

# ───────────────────────────────────────────────────────────────
# TAB 1 — BOLETOS IA
# ───────────────────────────────────────────────────────────────
with tab1:
    st.markdown("<p style='color:#8A97B5;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:18px;'>🌍 Copa del Mundo 2026 · Selecciona partidos a analizar</p>", unsafe_allow_html=True)
    with st.spinner("Sincronizando cuotas..."):
        datos_api = obtener_partidos_mundial()

    if isinstance(datos_api, dict) and "error" in datos_api:
        st.error(f"❌ Error API de cuotas: {datos_api['error']}")
    elif not datos_api:
        st.info("⏳ No hay partidos disponibles en este momento.")
    else:
        grupos = defaultdict(list)
        for p in datos_api[:16]:
            grupos[fmt_grupo(p["commence_time"])].append(p)

        partidos_activos = []
        for fecha_label, partidos_dia in grupos.items():
            n = len(partidos_dia)
            st.markdown(
                '<div class="date-sep">'
                f'<div class="date-badge">📅 {fecha_label}</div>'
                '<div class="date-line"></div>'
                f'<div class="date-cnt">{n} partido{"s" if n>1 else ""}</div>'
                '</div>', unsafe_allow_html=True)

            for p in partidos_dia:
                h2h  = extraer_h2h(p)
                home, away = p["home_team"], p["away_team"]
                hora = fmt_hora(p["commence_time"])
                if h2h:
                    pw,dw,aw = h2h["home"],h2h["draw"],h2h["away"]
                    ho,do_,ao = h2h["home_odd"],h2h["draw_odd"],h2h["away_odd"]
                    prob_html = (
                        '<div class="prob-wrap">'
                        '<div class="prob-labels">'
                        f'<span>{tr(home)}</span><span>Empate</span><span>{tr(away)}</span>'
                        '</div><div class="prob-bar">'
                        f'<div class="pb-h" style="width:{pw}%"></div>'
                        f'<div class="pb-d" style="width:{dw}%"></div>'
                        f'<div class="pb-a" style="width:{aw}%"></div>'
                        '</div><div class="prob-pcts">'
                        f'<span class="pct-h">{pw}%</span>'
                        f'<span class="pct-d">{dw}%</span>'
                        f'<span class="pct-a">{aw}%</span>'
                        '</div></div>')
                    c_home,c_draw,c_away = f"@{ho:.2f}",(f"@{do_:.2f}" if do_ else ""),f"@{ao:.2f}"
                else:
                    prob_html = ""; c_home = c_draw = c_away = ""

                t_h = ('<div class="team-blk">'
                       f'<div class="t-flag">{fl(home)}</div>'
                       f'<div class="t-name">{tr(home)}</div>'
                       + (f'<div class="t-cuota">{c_home}</div>' if c_home else '')
                       + '</div>')
                t_c = ('<div class="center-blk">'
                       f'<div class="mc-time">{hora}</div><div class="mc-vs">VS</div>'
                       + (f'<div class="mc-draw">{c_draw}</div>' if c_draw else '')
                       + '</div>')
                t_a = ('<div class="team-blk">'
                       f'<div class="t-flag">{fl(away)}</div>'
                       f'<div class="t-name">{tr(away)}</div>'
                       + (f'<div class="t-cuota">{c_away}</div>' if c_away else '')
                       + '</div>')
                st.markdown(
                    '<div class="mcard"><div class="teams-row">'
                    + t_h + t_c + t_a + '</div>' + prob_html + '</div>',
                    unsafe_allow_html=True)
                st.markdown('<div class="mcard-footer">', unsafe_allow_html=True)
                if st.checkbox(f"📌 Añadir — {tr(home)} vs {tr(away)}", key=p["id"]):
                    partidos_activos.append(p)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        n_sel = len(partidos_activos)
        if st.button(f"🚀 Construir Boletos · {n_sel} partido{'s' if n_sel!=1 else ''} seleccionado{'s' if n_sel!=1 else ''}"):
            if not partidos_activos:
                st.warning("⚠️ Selecciona al menos un partido.")
            else:
                with st.spinner("🤖 Calculando combinaciones de alta probabilidad..."):
                    res = ejecutar_algoritmo_quant(partidos_activos)
                if "error" in res:
                    st.error(f"❌ Error IA: {res['error']}")
                else:
                    st.session_state.ultimo_analisis    = res
                    st.session_state.partidos_analizados = " | ".join([f"{p['home_team']} vs {p['away_team']}" for p in partidos_activos])
                    st.session_state.ticket_guardado    = False

        if "ultimo_analisis" in st.session_state:
            data = st.session_state.ultimo_analisis
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("<p style='color:#EEF4FF;font-weight:800;font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;'>🎟️ Boletos Generados</p>", unsafe_allow_html=True)
            if data.get("game_script"):
                st.markdown(f"<p style='font-size:12px;color:#8A97B5;margin-bottom:18px;font-style:italic;'>💡 {tr_pick(data['game_script'])}</p>", unsafe_allow_html=True)

            def render_slip(clase, titulo, cuota, picks_html, desc):
                st.markdown(
                    f'<div class="tslip {clase}">'
                    f'<div class="slip-hdr"><span class="slip-tit">{titulo}</span><span class="slip-q">@{cuota}</span></div>'
                    + picks_html
                    + f'<div class="slip-desc"><b>Veredicto:</b> {tr_pick(desc)}</div></div>',
                    unsafe_allow_html=True)

            pe = data.get("pick_estrella",{})
            render_slip("slip-base","⭐ Pick Base (Single)",pe.get("cuota_betano","-"),
                f'<div class="i-match">{tr_pick(pe.get("partido",""))}</div><div class="i-bet">{tr_pick(pe.get("seleccion",""))}</div>',
                pe.get("razon_cuantitativa",""))
            ps = data.get("pick_mas_seguro",{})
            render_slip("slip-anti","🛡️ Pick Anti-Sorpresas",ps.get("cuota_betano","-"),
                f'<div class="i-match">{tr_pick(ps.get("partido",""))}</div><div class="i-bet">{tr_pick(ps.get("seleccion",""))}</div>',
                ps.get("razon_cuantitativa",""))
            estrat_map = {"segura":("slip-segura","🟢 COMBINADA SEGURA"),"moderada":("slip-moderada","🟡 COMBINADA MODERADA"),"arriesgada":("slip-arriesgada","🔴 COMBINADA ARRIESGADA")}
            for e in data.get("estrategias",[]):
                clase,tit = estrat_map.get(e.get("tipo","segura"),("slip-segura","Combinada"))
                ph = ""
                for pick in e.get("picks",[]):
                    p_str,b_str = (pick.split(":",1) if ":" in pick else ("Partido",pick))
                    ph += f'<div class="i-match">{tr_pick(p_str.strip())}</div><div class="i-bet">{tr_pick(b_str.strip())}</div>'
                render_slip(clase,tit,e.get("cuota_total","-"),ph,e.get("descripcion",""))
                # Mostrar advertencias de reglas de oro si las hay
                for aviso in e.get("advertencias",[]):
                    st.warning(aviso)

            if not st.session_state.get("ticket_guardado",False):
                st.markdown('<div class="btn-save">', unsafe_allow_html=True)
                if st.button("💾 Guardar Boletos en Base de Datos"):
                    if bd.guardar_ticket_db("FIFA World Cup", st.session_state.partidos_analizados, json.dumps(data, ensure_ascii=False)):
                        st.session_state.ticket_guardado = True; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Boletos guardados en la Base de Datos.")

# ───────────────────────────────────────────────────────────────
# TAB 2 — PREDICCIONES DIXON-COLES
# ───────────────────────────────────────────────────────────────
with tab2:
    comp_sel = st.selectbox("Competición", list(COMPETICIONES.keys()), key="comp_pred")
    comp_nombre, comp_season, comp_odds_key = COMPETICIONES[comp_sel]
    estado = modelo_mod.estado_modelo(comp_nombre, comp_season)

    c1,c2,c3 = st.columns(3)
    c1.metric("Partidos en BD",  estado["partidos_en_bd"])
    c2.metric("Finalizados",     estado["partidos_finalizados"])
    c3.metric("Equipos",         estado["n_equipos"])

    if not estado["listo"]:
        # ── Sin datos históricos: usar sistema Elo ──────────────
        st.info(f"⚡ Sin datos históricos suficientes ({estado['partidos_finalizados']} partidos). Usando predicciones por **Rating Elo** — sistema alternativo que no requiere API histórica.")

        ratings_elo = elo_mod.cargar_ratings()
        odds_lista  = obtener_odds_competicion(comp_odds_key)

        col_e1, col_e2 = st.columns(2)
        ver_pred_elo  = col_e1.button("🔮 Predicciones Elo")
        ver_rank_elo  = col_e2.button("🏅 Ranking Elo")

        if ver_rank_elo:
            ranking = elo_mod.ranking_elo(ratings_elo)
            st.markdown("**🏅 Ranking por Rating Elo**")
            for i,eq in enumerate(ranking[:15],1):
                c1,c2,c3 = st.columns([1,4,2])
                c1.markdown(f"**#{i}**")
                c2.markdown(f"**{tr(eq['equipo'])}**")
                c3.metric("Elo", eq["elo"])

        if ver_pred_elo:
            proximos = datos_mod.get_proximos_para_predecir(comp_nombre)
            if not proximos:
                st.warning("Sin partidos próximos en BD. Ve a ⚙️ Sistema → Sincronizar.")
            else:
                st.markdown(f"<p style='color:#8A97B5;font-size:12px;font-weight:700;margin-bottom:14px;'>📋 {len(proximos)} próximos · Predicciones Elo</p>", unsafe_allow_html=True)
                for partido in proximos[:8]:
                    home = partido["home_team"]; away = partido["away_team"]
                    hora = fmt_hora(partido.get("fecha",""))
                    pred = elo_mod.calcular_probabilidades(home, away, ratings_elo)
                    cuotas = emparejar_partido(home, away, odds_lista) if odds_lista else {}
                    picks  = elo_mod.detectar_valor_elo(home, away, cuotas, ratings_elo) if cuotas else []
                    ph = int(pred["prob_home"]*100)
                    pd_ = int(pred["prob_draw"]*100)
                    pa = int(pred["prob_away"]*100)
                    picks_html = ""
                    for pk in picks[:3]:
                        cls = "ev-badge" if pk["valor_esperado"]>7 else "ev-badge-mod"
                        picks_html += f'<span class="{cls}">🎯 {tr_pick(pk["seleccion"])} @{pk["cuota"]} · +{pk["valor_esperado"]:.1f}% EV · Kelly {pk["kelly_pct"]}%</span>'
                    ev_sec = (f'<div style="margin-top:10px;padding-top:10px;border-top:1px dashed rgba(255,255,255,.07);">{picks_html}</div>' if picks_html else "")
                    st.markdown(
                        '<div class="pred-card">'
                        '<div class="pred-teams">'
                        f'<span class="pred-team">{fl(home)} {tr(home)}</span>'
                        f'<span class="pred-time">{hora}</span>'
                        f'<span class="pred-team">{tr(away)} {fl(away)}</span>'
                        '</div>'
                        '<div class="prob-bar" style="height:10px;border-radius:5px;margin-bottom:6px;">'
                        f'<div class="pb-h" style="width:{ph}%"></div>'
                        f'<div class="pb-d" style="width:{pd_}%"></div>'
                        f'<div class="pb-a" style="width:{pa}%"></div>'
                        '</div>'
                        '<div class="prob-pcts">'
                        f'<span class="pct-h">{ph}%</span>'
                        f'<span class="pct-d">{pd_}%</span>'
                        f'<span class="pct-a">{pa}%</span>'
                        '</div>'
                        f'<div style="font-size:10px;color:#8A97B5;margin-top:6px;">🎯 Goles esperados: <b style="color:#EEF4FF;">{pred["lambda_home"]:.2f}</b> — <b style="color:#EEF4FF;">{pred["lambda_away"]:.2f}</b> · Probable: <b style="color:#00C2FF;">{pred["marcador_probable"]}</b> · Elo: {pred["elo_home"]} vs {pred["elo_away"]}</div>'
                        + ev_sec + '</div>',
                        unsafe_allow_html=True)

        # Botón actualizar Elo desde resultados reales
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Actualizar ratings Elo con resultados reales"):
            scores_raw = bd.get_partidos_terminados(comp_nombre, comp_season)
            if scores_raw:
                with st.spinner("Actualizando ratings Elo..."):
                    nuevos = elo_mod.actualizar_desde_scores(scores_raw)
                st.success(f"✅ Ratings Elo actualizados con {len(scores_raw)} partidos.")
    else:
        if estado["modelo_entrenado"]:
            st.success(f"✅ Modelo entrenado · {estado['n_partidos_usados']} partidos · Ventaja local: +{estado['home_advantage']:.3f}")

        col_b1, col_b2 = st.columns(2)
        generar     = col_b1.button("🔮 Generar Predicciones")
        ver_ranking = col_b2.button("🏅 Ranking de Equipos")

        if ver_ranking:
            ranking = modelo_mod.ranking_equipos(comp_nombre, comp_season)
            if ranking:
                st.markdown("**🏅 Top 10 según el modelo Dixon-Coles**")
                for i,eq in enumerate(ranking[:10],1):
                    ca,cb,cc,cd = st.columns([1,3,1,1])
                    ca.markdown(f"**#{i}**")
                    cb.markdown(f"**{tr(eq['equipo'])}**")
                    cc.metric("Ataque",f"{eq['ataque']:+.3f}")
                    cd.metric("Rating",f"{eq['rating']:+.3f}")
            else:
                st.info("Sin datos para el ranking.")

        if generar:
            with st.spinner("🔮 Calculando predicciones Dixon-Coles..."):
                odds_lista = obtener_odds_competicion(comp_odds_key)
                proximos   = datos_mod.get_proximos_para_predecir(comp_nombre)
                params     = modelo_mod.entrenar_modelo(comp_nombre, comp_season)

            if not params:
                st.error("❌ No hay suficientes datos para el modelo.")
            elif not proximos:
                st.info("ℹ️ No hay partidos próximos en la BD. Sincroniza desde ⚙️ Sistema.")
            else:
                st.markdown(f"<p style='color:#8A97B5;font-size:12px;font-weight:700;margin-bottom:14px;'>📋 {len(proximos)} próximos partidos</p>", unsafe_allow_html=True)
                total_ev = 0
                for partido in proximos[:8]:
                    home = partido["home_team"]; away = partido["away_team"]
                    hora = fmt_hora(partido.get("fecha",""))
                    pred = modelo_mod.predecir_partido(home, away, params)
                    if not pred: continue
                    cuotas = emparejar_partido(home, away, odds_lista) if odds_lista else {}
                    picks  = modelo_mod.detectar_valor(pred, cuotas) if cuotas else []
                    total_ev += len(picks)
                    ph = int(pred["prob_home"]*100)
                    pd_ = int(pred["prob_draw"]*100)
                    pa = int(pred["prob_away"]*100)
                    picks_html = ""
                    for pk in picks[:3]:
                        cls = "ev-badge" if pk["valor_esperado"]>7 else "ev-badge-mod"
                        picks_html += f'<span class="{cls}">🎯 {tr_pick(pk["seleccion"])} @{pk["cuota"]} · +{pk["valor_esperado"]:.1f}% EV · Kelly {pk["kelly_pct"]}%</span>'
                    ev_sec = (f'<div style="margin-top:10px;padding-top:10px;border-top:1px dashed rgba(255,255,255,.07);">{picks_html}</div>' if picks_html else "")
                    st.markdown(
                        '<div class="pred-card">'
                        '<div class="pred-teams">'
                        f'<span class="pred-team">{fl(home)} {tr(home)}</span>'
                        f'<span class="pred-time">{hora}</span>'
                        f'<span class="pred-team">{tr(away)} {fl(away)}</span>'
                        '</div>'
                        '<div class="prob-bar" style="height:10px;border-radius:5px;margin-bottom:6px;">'
                        f'<div class="pb-h" style="width:{ph}%"></div>'
                        f'<div class="pb-d" style="width:{pd_}%"></div>'
                        f'<div class="pb-a" style="width:{pa}%"></div>'
                        '</div>'
                        '<div class="prob-pcts">'
                        f'<span class="pct-h">{ph}%</span>'
                        f'<span class="pct-d">{pd_}%</span>'
                        f'<span class="pct-a">{pa}%</span>'
                        '</div>'
                        f'<div style="font-size:10px;color:#8A97B5;margin-top:6px;">⚽ Goles esperados: <b style="color:#EEF4FF;">{pred["lambda_home"]:.2f}</b> — <b style="color:#EEF4FF;">{pred["lambda_away"]:.2f}</b> · Probable: <b style="color:#00C2FF;">{pred["marcador_probable"]}</b></div>'
                        + ev_sec + '</div>',
                        unsafe_allow_html=True)

                    if picks:
                        with st.expander(f"🔍 Análisis IA — {tr(home)} vs {tr(away)}"):
                            if st.button("🤖 Analizar contexto con Gemini", key=f"ctx_{partido['id']}"):
                                with st.spinner("Buscando noticias actuales..."):
                                    ctx = gemini_mod.analizar_contexto_partido(home, away, comp_nombre, pred)
                                if ctx:
                                    st.markdown(f"**Lesiones {tr(home)}:** {ctx.get('lesiones_home',{}).get('detalle','N/D')}")
                                    st.markdown(f"**Lesiones {tr(away)}:** {ctx.get('lesiones_away',{}).get('detalle','N/D')}")
                                    st.markdown(f"**Forma local:** {ctx.get('forma_home',{}).get('ultimos_5','N/D')}")
                                    st.markdown(f"**Forma visitante:** {ctx.get('forma_away',{}).get('ultimos_5','N/D')}")
                                    st.markdown(f"**Ajuste sugerido:** {ctx.get('ajuste_sugerido',{}).get('razon','Sin cambios')}")
                                    st.info(ctx.get('resumen',''))

                if total_ev == 0:
                    st.info("ℹ️ El modelo no detectó picks con +EV. El mercado refleja bien las probabilidades para estos partidos.")

# ───────────────────────────────────────────────────────────────
# TAB 3 — ESTADÍSTICAS
# ───────────────────────────────────────────────────────────────
with tab3:
    comp_stats = st.selectbox("Competición", list(COMPETICIONES.keys()), key="comp_stats")
    comp_nombre_s = COMPETICIONES[comp_stats][0]
    stats = bd.get_estadisticas_modelo(comp_nombre_s)
    color = "#00E676" if stats["hit_rate"]>=55 else "#FFB700" if stats["hit_rate"]>=45 else "#FF3B5C"
    roi_color = "#00E676" if stats["roi"]>=0 else "#FF3B5C"

    st.markdown(
        '<div class="dash-grid">'
        f'<div class="d-card"><div class="d-val" style="color:{color};">{stats["hit_rate"]}%</div><div class="d-lbl">Hit Rate</div></div>'
        f'<div class="d-card"><div class="d-val" style="color:{roi_color};">{stats["roi"]:+.1f}%</div><div class="d-lbl">ROI</div></div>'
        f'<div class="d-card"><div class="d-val" style="color:#8B5CF6;">{stats["total"]}</div><div class="d-lbl">Total Picks</div></div>'
        '</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    c1.metric("✅ Acertados", stats["acertados"])
    c2.metric("❌ Fallidos",  stats["fallidos"])

    mejores = bd.get_mejor_mercado(comp_nombre_s)
    if mejores:
        st.markdown("<p style='color:#EEF4FF;font-weight:800;font-size:13px;margin-top:18px;margin-bottom:10px;'>📈 Rendimiento por Mercado</p>", unsafe_allow_html=True)
        for m in mejores:
            rc = "#00E676" if m["roi"]>=0 else "#FF3B5C"
            st.markdown(
                '<div class="hist-row">'
                f'<div><div class="h-meta">{m["mercado"]}</div>'
                f'<div class="h-txt">{m["total"]} picks · {m["hit_rate"]}% acierto</div></div>'
                f'<span class="h-badge" style="background:{rc}20;color:{rc};border:1px solid {rc}40;">ROI {m["roi"]:+.1f}%</span>'
                '</div>', unsafe_allow_html=True)

    st.markdown("<p style='color:#EEF4FF;font-weight:800;font-size:13px;margin-top:18px;margin-bottom:10px;'>📋 Historial Picks +EV</p>", unsafe_allow_html=True)
    historial_ev = bd.get_valores_por_competicion(comp_nombre_s, limit=20)
    if not historial_ev:
        st.info("Sin historial de picks. Genera predicciones en 🔮.")
    else:
        for pick in historial_ev:
            estado = pick.get("resultado","pendiente")
            bg = "#00E676" if estado=="acertado" else "#FF3B5C" if estado=="fallido" else "#4A5568"
            st.markdown(
                f'<div class="hist-row" style="border-left-color:{bg};">'
                f'<div><div class="h-meta">{tr_pick(pick.get("home_team",""))} vs {tr_pick(pick.get("away_team",""))}</div>'
                f'<div class="h-txt">{pick.get("mercado","")} · {tr_pick(pick.get("seleccion",""))} @{pick.get("cuota",0):.2f} · EV {pick.get("valor_esperado",0)*100:+.1f}%</div></div>'
                f'<span class="h-badge" style="background:{bg};color:#fff;">{estado}</span>'
                '</div>', unsafe_allow_html=True)
            c1,c2,c3,_ = st.columns([1,1,1,3])
            if c1.button("✅",key=f"ev_ok_{pick['id']}"): bd.actualizar_resultado_valor(pick["id"],"acertado"); st.rerun()
            if c2.button("❌",key=f"ev_fa_{pick['id']}"): bd.actualizar_resultado_valor(pick["id"],"fallido"); st.rerun()
            if c3.button("⏳",key=f"ev_pe_{pick['id']}"): bd.actualizar_resultado_valor(pick["id"],"pendiente"); st.rerun()

    st.markdown("<p style='color:#EEF4FF;font-weight:800;font-size:13px;margin-top:18px;margin-bottom:10px;'>🎟️ Historial Boletos IA</p>", unsafe_allow_html=True)
    with st.spinner("Cargando..."):
        auto_verificar_jornada()
        historial_ia = bd.cargar_historial_db()

    if not historial_ia:
        st.info("Sin boletos guardados todavía.")
    else:
        for t in historial_ia:
            data_t = json.loads(t["analisis_json"])
            ests   = data_t.get("estrategias",[])
            with st.expander(f"🎫 {t['fecha_gen']} · {t['liga']}"):
                st.markdown(f"<div style='font-size:10px;color:#8A97B5;margin-bottom:10px;'><b>Partidos:</b> {tr_pick(t['partidos'])}</div>", unsafe_allow_html=True)
                items = [
                    ("res_estrella",   "⭐ Pick Base",     tr_pick(data_t.get("pick_estrella",{}).get("seleccion","N/D"))),
                    ("res_mas_seguro", "🛡️ Anti-Sorp.",    tr_pick(data_t.get("pick_mas_seguro",{}).get("seleccion","N/D"))),
                    ("res_segura",     "🟢 Segura",    f"@{ests[0].get('cuota_total','?')}" if len(ests)>0 else "N/D"),
                    ("res_moderada",   "🟡 Moderada",  f"@{ests[1].get('cuota_total','?')}" if len(ests)>1 else "N/D"),
                    ("res_arriesgada", "🔴 Arriesgada",f"@{ests[2].get('cuota_total','?')}" if len(ests)>2 else "N/D"),
                ]
                for col_name,titulo,sel_txt in items:
                    estado = t.get(col_name,"pendiente")
                    bg = "#00E676" if estado=="acertado" else "#FF3B5C" if estado=="fallido" else "#4A5568"
                    st.markdown(
                        f'<div class="hist-row" style="border-left-color:{bg};">'
                        f'<div><div class="h-meta">{titulo}</div><div class="h-txt">{sel_txt}</div></div>'
                        f'<span class="h-badge" style="background:{bg};color:#fff;">{estado}</span></div>',
                        unsafe_allow_html=True)
                    c1,c2,c3,_ = st.columns([1,1,1,3])
                    if c1.button("✅",key=f"ia_ok_{t['id']}_{col_name}"): bd.actualizar_resultado_historial(t["id"],col_name,"acertado"); st.rerun()
                    if c2.button("❌",key=f"ia_fa_{t['id']}_{col_name}"): bd.actualizar_resultado_historial(t["id"],col_name,"fallido"); st.rerun()
                    if c3.button("⏳",key=f"ia_pe_{t['id']}_{col_name}"): bd.actualizar_resultado_historial(t["id"],col_name,"pendiente"); st.rerun()
                st.markdown("<hr style='border-color:rgba(255,255,255,0.05);margin:8px 0;'>",unsafe_allow_html=True)
                if st.button("🗑️ Eliminar",key=f"ia_del_{t['id']}"): bd.eliminar_ticket_db(t["id"]); st.rerun()

# ───────────────────────────────────────────────────────────────
# TAB 4 — SISTEMA
# ───────────────────────────────────────────────────────────────
with tab4:
    comp_sys = st.selectbox("Competición", list(COMPETICIONES.keys()), key="comp_sys")
    comp_nombre_sys, comp_season_sys, _ = COMPETICIONES[comp_sys]
    estado_sys = modelo_mod.estado_modelo(comp_nombre_sys, comp_season_sys)

    st.markdown('<div class="sys-card"><div class="sys-title">📡 Estado Actual</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.metric("Total",      estado_sys["partidos_en_bd"])
    c2.metric("Finalizados",estado_sys["partidos_finalizados"])
    c3.metric("Pendientes", estado_sys["partidos_pendientes"])
    model_ok = "✅ Entrenado" if estado_sys["modelo_entrenado"] else "⏳ Sin datos suficientes"
    st.markdown(
        f"<p style='font-size:12px;color:#8A97B5;margin-top:8px;'>"
        f"Modelo: <b style='color:#EEF4FF;'>{model_ok}</b> · "
        f"Equipos: <b style='color:#EEF4FF;'>{estado_sys['n_equipos']}</b> · "
        f"Partidos usados: <b style='color:#EEF4FF;'>{estado_sys['n_partidos_usados']}</b></p>",
        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sys-card"><div class="sys-title">🔄 Sincronización · Football-Data.org (1 llamada)</div>', unsafe_allow_html=True)
    col_s1,col_s2 = st.columns(2)
    with col_s1:
        if st.button("📥 Sincronizar todos los partidos"):
            codigo = datos_mod.COMPETICIONES.get(comp_nombre_sys,"")
            if not codigo:
                st.error("Código de competición no encontrado.")
            else:
                with st.spinner(f"Descargando {comp_nombre_sys}..."):
                    resultado = datos_mod.sincronizar_competicion(comp_nombre_sys, codigo, comp_season_sys)
                if resultado.get("ok"):
                    st.success(resultado["mensaje"])
                    modelo_mod.entrenar_modelo.clear()
                    st.rerun()
                else:
                    st.error(resultado.get("mensaje","Error"))
    with col_s2:
        if st.button("🔄 Actualizar resultados"):
            codigo = datos_mod.COMPETICIONES.get(comp_nombre_sys,"")
            if codigo:
                with st.spinner("Actualizando resultados..."):
                    resultado = datos_mod.actualizar_resultados(comp_nombre_sys, codigo, comp_season_sys)
                if resultado.get("ok"):
                    st.success(resultado["mensaje"])
                    modelo_mod.entrenar_modelo.clear()
                else:
                    st.error(resultado.get("mensaje","Error"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sys-card"><div class="sys-title">🧠 Modelo Dixon-Coles</div>', unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px;color:#8A97B5;margin-bottom:10px;'>El modelo se reentrena automáticamente. Caché de 1 hora.</p>", unsafe_allow_html=True)
    if st.button("♻️ Forzar reentrenamiento"):
        modelo_mod.entrenar_modelo.clear()
        with st.spinner("Reentrenando modelo..."):
            params_new = modelo_mod.entrenar_modelo(comp_nombre_sys, comp_season_sys)
        if params_new:
            st.success(f"✅ Reentrenado con {params_new['n_partidos']} partidos. Convergió: {params_new['convergido']}")
        else:
            st.warning("⚠️ Sin partidos suficientes. Sincroniza primero.")
    st.markdown('</div>', unsafe_allow_html=True)

    plan = datos_mod.plan_llamadas_diario()
    st.markdown(
        '<div class="sys-card"><div class="sys-title">📊 Gestión de Llamadas API</div>'
        f'<p style="font-size:12px;color:#8A97B5;">Límite diario: <b style="color:#EEF4FF;">{plan["limite_diario"]}</b> · '
        f'Uso recomendado: <b style="color:#00C2FF;">{plan["llamadas_reservadas"]} llamadas</b> · '
        f'Margen libre: <b style="color:#00E676;">{plan["llamadas_disponibles_extras"]}</b></p>'
        '</div>', unsafe_allow_html=True)
