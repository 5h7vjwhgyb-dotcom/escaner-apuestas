import streamlit as st
import requests
import re
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
import json
from supabase import create_client, Client
from collections import defaultdict

def compact(html_str):
    """Colapsa HTML multi-línea a una sola línea.
    Evita que el parser de Markdown de Streamlit interprete líneas
    con sangría como bloques de código (≥4 espacios = <pre><code>)."""
    return re.sub(r'\n\s*', '', str(html_str))

# ─── Zona Horaria Chile ─────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-4))

# ═══════════════════════════════════════════════════════════════
# TRADUCCIONES Y BANDERAS
# ═══════════════════════════════════════════════════════════════
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
    "Algeria":"Argelia","Kenya":"Kenia","Zimbabwe":"Zimbabue",
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
    "Algeria":"🇩🇿","Kenya":"🇰🇪","Zimbabwe":"🇿🇼",
}
DIAS_ES = {
    "Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
    "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo",
}
MESES_ES = {
    "Jan":"Ene","Feb":"Feb","Mar":"Mar","Apr":"Abr","May":"May","Jun":"Jun",
    "Jul":"Jul","Aug":"Ago","Sep":"Sep","Oct":"Oct","Nov":"Nov","Dec":"Dic",
}

def tr(n):
    return PAISES_ES.get(n, n)

def fl(n):
    return FLAGS.get(n, "🌍")

def tr_pick(texto):
    """Traduce nombres de países en textos de picks (más largos primero para evitar colisiones)."""
    for en, es in sorted(PAISES_ES.items(), key=lambda x: -len(x[0])):
        texto = texto.replace(en, es)
    return texto

def extraer_h2h(partido):
    """Extrae cuotas H2H y calcula probabilidades implícitas normalizadas."""
    home, away = partido.get("home_team", ""), partido.get("away_team", "")
    for bm in partido.get("bookmakers", []):
        for mkt in bm.get("markets", []):
            if mkt.get("key") == "h2h":
                cuotas = {o["name"]: o["price"] for o in mkt.get("outcomes", [])}
                ho = cuotas.get(home, 0)
                do = cuotas.get("Draw", 0)
                ao = cuotas.get(away, 0)
                if ho and ao:
                    ph = 1 / ho
                    pd = 1 / do if do else 0
                    pa = 1 / ao
                    t  = ph + pd + pa
                    return {
                        "home": round(ph / t * 100),
                        "draw": round(pd / t * 100) if do else 0,
                        "away": round(pa / t * 100),
                        "home_odd": ho,
                        "draw_odd": do,
                        "away_odd": ao,
                    }
    return None

def fmt_grupo(iso):
    try:
        dt  = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ_CHILE)
        dia = DIAS_ES.get(dt.strftime("%A"), dt.strftime("%A"))
        mes = MESES_ES.get(dt.strftime("%b"), dt.strftime("%b"))
        return f"{dia} {dt.day} {mes}"
    except:
        return "Próximamente"

def fmt_hora(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ_CHILE).strftime("%H:%M")
    except:
        return "N/D"

def fmt_fecha(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ_CHILE).strftime("%d %b · %H:%M")
    except:
        return "Fecha N/D"

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y ESTILOS
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡COMBINADAS", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

  /* ── Base ── */
  [data-testid="stAppViewContainer"]{background:#07101E!important;color:#EEF4FF!important;font-family:'Inter',sans-serif!important;}
  [data-testid="stHeader"]{background:transparent!important;}
  .block-container{padding-top:1rem!important;max-width:680px!important;}

  /* ── Header ── */
  .hdr{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;background:linear-gradient(135deg,#0D1B2E,#0E2040);border:1px solid rgba(0,194,255,.12);border-radius:16px;margin-bottom:22px;box-shadow:0 4px 30px rgba(0,0,0,.4);}
  .logo{font-size:22px;font-weight:900;letter-spacing:-1px;color:#fff;}
  .logo-bolt{color:#00C2FF;text-shadow:0 0 20px rgba(0,194,255,.6);}
  .badge{background:rgba(255,107,0,.15);border:1px solid rgba(255,107,0,.35);padding:5px 13px;border-radius:20px;font-size:10px;font-weight:800;color:#FF6B00;text-transform:uppercase;letter-spacing:.5px;}

  /* ── Tabs ── */
  [data-testid="stTabs"] [data-baseweb="tab-list"]{background:#0A1525!important;border-radius:10px!important;padding:4px!important;gap:4px!important;}
  [data-testid="stTabs"] button{border-radius:8px!important;font-weight:700!important;font-size:13px!important;color:#8A97B5!important;transition:all .2s!important;}
  [data-testid="stTabs"] button[aria-selected="true"]{background:#0E1A2C!important;color:#00C2FF!important;box-shadow:0 2px 8px rgba(0,0,0,.3)!important;}

  /* ── Botones Streamlit ── */
  .stButton>button{background:linear-gradient(135deg,#00C2FF,#0080CC)!important;border:none!important;border-radius:10px!important;color:#fff!important;font-weight:800!important;font-size:14px!important;width:100%!important;padding:.85em!important;transition:all .2s!important;letter-spacing:.3px!important;box-shadow:0 4px 15px rgba(0,194,255,.2)!important;}
  .stButton>button:hover{opacity:.92!important;transform:translateY(-1px)!important;box-shadow:0 6px 22px rgba(0,194,255,.35)!important;}
  .btn-save>button{background:linear-gradient(135deg,#8B5CF6,#6D28D9)!important;box-shadow:0 4px 15px rgba(139,92,246,.25)!important;}
  .btn-save>button:hover{box-shadow:0 6px 22px rgba(139,92,246,.4)!important;}

  /* ── Separador de Fecha ── */
  .date-sep{display:flex;align-items:center;gap:10px;margin:28px 0 14px;}
  .date-badge{background:rgba(0,194,255,.08);border:1px solid rgba(0,194,255,.2);color:#00C2FF;font-size:10px;font-weight:800;padding:5px 14px;border-radius:20px;text-transform:uppercase;letter-spacing:.8px;white-space:nowrap;}
  .date-cnt{background:rgba(255,255,255,.06);color:#8A97B5;font-size:10px;font-weight:700;padding:4px 10px;border-radius:10px;white-space:nowrap;}
  .date-line{flex:1;height:1px;background:linear-gradient(90deg,rgba(0,194,255,.15),transparent);}

  /* ── Match Card ── */
  .mcard{
    background:linear-gradient(145deg,#0D1B2E,#0B1725);
    border:1px solid rgba(255,255,255,.08);
    border-bottom:none;
    border-radius:16px 16px 0 0;
    padding:18px 20px 16px;
    margin-bottom:0;
    box-shadow:0 2px 16px rgba(0,0,0,.25);
    position:relative;
    overflow:hidden;
  }
  .mcard::after{
    content:'';position:absolute;top:0;right:0;
    width:120px;height:120px;
    background:radial-gradient(circle,rgba(0,194,255,.04),transparent 70%);
    pointer-events:none;
  }

  /* ── Equipos ── */
  .teams-row{display:grid;grid-template-columns:1fr 88px 1fr;align-items:center;gap:8px;margin-bottom:16px;}
  .team-blk{display:flex;flex-direction:column;align-items:center;gap:5px;}
  .t-flag{font-size:38px;line-height:1;filter:drop-shadow(0 3px 6px rgba(0,0,0,.4));}
  .t-name{font-size:12px;font-weight:800;color:#EEF4FF;text-align:center;line-height:1.2;max-width:110px;}
  .t-cuota{font-size:10px;color:#8B5CF6;font-weight:700;background:rgba(139,92,246,.1);padding:2px 7px;border-radius:6px;}

  /* ── Centro del partido ── */
  .center-blk{display:flex;flex-direction:column;align-items:center;gap:3px;}
  .mc-time{font-size:22px;font-weight:900;color:#00C2FF;letter-spacing:-1.5px;line-height:1;text-shadow:0 0 20px rgba(0,194,255,.4);}
  .mc-vs{font-size:9px;font-weight:800;color:#2A3C52;letter-spacing:2.5px;text-transform:uppercase;}
  .mc-draw{font-size:10px;color:#8A97B5;font-weight:700;background:rgba(255,255,255,.05);padding:2px 7px;border-radius:6px;}

  /* ── Barras de Probabilidad ── */
  .prob-wrap{margin-top:4px;}
  .prob-labels{display:flex;justify-content:space-between;font-size:9px;color:#8A97B5;font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:.3px;}
  .prob-bar{display:flex;height:7px;border-radius:4px;overflow:hidden;gap:2px;}
  .pb-h{background:linear-gradient(90deg,#00C2FF,#0099D9);border-radius:4px 0 0 4px;}
  .pb-d{background:#7C4DFF;}
  .pb-a{background:linear-gradient(90deg,#FF6B6B,#FF3B5C);border-radius:0 4px 4px 0;}
  .prob-pcts{display:flex;justify-content:space-between;font-size:11px;font-weight:800;margin-top:6px;}
  .pct-h{color:#00C2FF;}
  .pct-d{color:#9B71FF;}
  .pct-a{color:#FF6B6B;}

  /* ── Footer de la Card (Checkbox) ── */
  .mcard-footer{
    background:#091420;
    border:1px solid rgba(255,255,255,.08);
    border-top:1px dashed rgba(0,194,255,.1);
    border-radius:0 0 16px 16px;
    padding:6px 20px;
    margin-bottom:16px;
  }
  .mcard-footer [data-testid="stCheckbox"]{
    background:transparent!important;
    border:none!important;
    padding:4px 0!important;
    margin:0!important;
  }
  .mcard-footer label p{
    font-size:11px!important;
    font-weight:700!important;
    color:#8A97B5!important;
    text-transform:uppercase!important;
    letter-spacing:.6px!important;
  }
  .mcard-footer [data-testid="stCheckbox"] input:checked + div{
    background:#00C2FF!important;
    border-color:#00C2FF!important;
  }

  /* ── Boletos / Tickets ── */
  .tslip{background:linear-gradient(145deg,#101C2E,#0D1828);border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:18px 20px;margin-bottom:16px;position:relative;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.25);}
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

  /* ── Dashboard Estadísticas ── */
  .dash-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:22px;}
  .d-card{background:linear-gradient(145deg,#0D1B2E,#0B1725);border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:16px;text-align:center;}
  .d-val{font-size:26px;font-weight:900;color:#fff;margin-bottom:4px;letter-spacing:-1px;}
  .d-lbl{font-size:10px;font-weight:700;color:#8A97B5;text-transform:uppercase;letter-spacing:.5px;}

  /* ── Historial ── */
  .hist-row{display:flex;justify-content:space-between;align-items:center;background:#0E1A2C;padding:12px 14px;border-radius:9px;margin-bottom:8px;border-left:3px solid #4A5568;}
  .h-meta{font-size:12px;color:#EEF4FF;font-weight:800;margin-bottom:2px;}
  .h-txt{font-size:11px;color:#8A97B5;}
  .h-badge{font-size:10px;font-weight:800;text-transform:uppercase;padding:3px 9px;border-radius:5px;letter-spacing:.5px;}

  /* ── Spinner ── */
  .stSpinner>div{border-top-color:#00C2FF!important;}

  /* ── Success/Warning/Error ── */
  [data-testid="stAlert"]{border-radius:10px!important;}
</style>

<div class="hdr">
  <div class="logo">BET<span class="logo-bolt">⚡</span>COMBINADAS</div>
  <div class="badge">🎯 MUNDIAL & BETANO</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# CONEXIONES (Supabase y APIs)
# ═══════════════════════════════════════════════════════════════
api_gemini = st.secrets.get("GEMINI_API", "") or st.session_state.get("_gem", "")
api_odds   = st.secrets.get("ODDS_API", "")   or st.session_state.get("_odd", "")
supa_url   = st.secrets.get("SUPABASE_URL", "") or st.session_state.get("_supa_url", "")
supa_key   = st.secrets.get("SUPABASE_KEY", "") or st.session_state.get("_supa_key", "")

if not (api_gemini and api_odds and supa_url and supa_key):
    st.warning("⚠️ Configura las credenciales en Streamlit Secrets para iniciar.")
    st.stop()

supabase: Client = create_client(supa_url, supa_key)

# ═══════════════════════════════════════════════════════════════
# BASE DE DATOS Y VERIFICADOR AUTÓNOMO
# ═══════════════════════════════════════════════════════════════
def auto_verificar_jornada():
    """Motor que lee marcadores finales y evalúa tickets pendientes."""
    try:
        pendientes = supabase.table("historial").select("*").or_(
            "res_estrella.eq.pendiente,res_mas_seguro.eq.pendiente,res_segura.eq.pendiente,res_moderada.eq.pendiente,res_arriesgada.eq.pendiente"
        ).execute().data
        if not pendientes: return

        url_scores = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/scores/?apiKey={api_odds}&daysFrom=3"
        r = requests.get(url_scores, timeout=10)
        if r.status_code != 200: return

        marcadores = r.json()
        partidos_terminados = {}
        for m in marcadores:
            if m.get("completed", False):
                home, away = m.get("home_team"), m.get("away_team")
                scores = m.get("scores", [])
                if len(scores) == 2:
                    s1, s2 = int(scores[0]["score"]), int(scores[1]["score"])
                    partidos_terminados[f"{home} vs {away}"] = f"FINAL: {home} {s1} - {s2} {away}"

        if not partidos_terminados: return

        client = genai.Client(api_key=api_gemini)
        for ticket in pendientes:
            data_a = json.loads(ticket["analisis_json"])
            updates = {}
            estrategias = data_a.get("estrategias", [])
            columnas = [
                ("res_estrella",   data_a.get("pick_estrella", {})),
                ("res_mas_seguro", data_a.get("pick_mas_seguro", {})),
                ("res_segura",     estrategias[0] if len(estrategias) > 0 else {}),
                ("res_moderada",   estrategias[1] if len(estrategias) > 1 else {}),
                ("res_arriesgada", estrategias[2] if len(estrategias) > 2 else {}),
            ]
            for col, obj in columnas:
                if ticket.get(col) != "pendiente" or not obj: continue
                apuesta_txt = obj.get("seleccion", "") or " | ".join(obj.get("picks", []))
                partidos_del_ticket = [p for p in partidos_terminados if p in ticket["partidos"] or p in apuesta_txt]
                if partidos_del_ticket:
                    marcas_str = "\n".join([partidos_terminados[p] for p in partidos_del_ticket])
                    prompt = f"""
Evalúa si esta apuesta se GANÓ o PERDIÓ según los marcadores finales.
MARCADORES: {marcas_str}
APUESTA: {apuesta_txt}
Si todos los picks se cumplieron → responde solo "acertado".
Si al menos un pick falló → responde solo "fallido".
Si faltan resultados → responde solo "pendiente"."""
                    try:
                        res = client.models.generate_content(
                            model="gemini-2.0-flash-lite", contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.0)
                        ).text.strip().lower()
                        if "acertado" in res:   updates[col] = "acertado"
                        elif "fallido" in res:  updates[col] = "fallido"
                    except: pass
            if updates:
                supabase.table("historial").update(updates).eq("id", ticket["id"]).execute()
    except: pass

def guardar_ticket_db(liga, partidos_str, analisis_json):
    fecha = datetime.now(TZ_CHILE).strftime("%Y-%m-%d %H:%M")
    data = {
        "fecha_gen": fecha, "liga": liga,
        "partidos": partidos_str,
        "analisis_json": json.dumps(analisis_json, ensure_ascii=False),
    }
    try: supabase.table("historial").insert(data).execute(); return True
    except: return False

def cargar_historial_db():
    try: return supabase.table("historial").select("*").order("id", desc=True).limit(30).execute().data
    except: return []

def actualizar_resultado_manual(tid, campo, valor):
    supabase.table("historial").update({campo: valor}).eq("id", tid).execute()

def eliminar_ticket_db(tid):
    supabase.table("historial").delete().eq("id", tid).execute()

# ═══════════════════════════════════════════════════════════════
# INTELIGENCIA QUANT
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_partidos_mundial(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h,totals,spreads"
    try:
        r = requests.get(url, timeout=10); r.raise_for_status(); return r.json()
    except Exception as e: return {"error": str(e)}

@st.cache_data(ttl=86400, show_spinner=False)
def ejecutar_algoritmo_quant(api_key, partidos_seleccionados):
    prompt = f"""
Eres un Analista Experto en Apuestas Deportivas. Tu único objetivo es GANAR DINERO construyendo boletos con la máxima probabilidad de acierto para el Mundial de la FIFA.

REGLA 1 (FILOSOFÍA): Busca opciones de altísima probabilidad con cuotas bajas (@1.20 a @1.40).

REGLA 2 (ANTI-CORRELACIÓN ¡ESTRICTO!): NUNCA mezcles "Ganador Directo" y "Hándicap" del MISMO partido. O usas ganador, o usas hándicap.

MERCADOS PERMITIDOS: Ganador (1X2), Doble Oportunidad, Goles (Over/Under 0.5-5.5), Córners, Tarjetas, Hándicap.

ESTRUCTURA OBLIGATORIA:
- SEGURA: 1-2 picks. Cuotas @1.20-@1.40.
- MODERADA: 3-4 picks. Cuota total @1.50-@3.50.
- ARRIESGADA: 3-5 picks. Cuota total @3.50-@7.00.

PARTIDOS EN CRUDO:
{json.dumps(partidos_seleccionados, ensure_ascii=False, indent=2)}

Responde ÚNICAMENTE con este JSON estructurado (sin texto extra, sin bloques markdown):
{{
  "game_script": "Análisis breve de las mejores oportunidades.",
  "pick_estrella": {{"partido":"Eq A vs Eq B","categoria_permitida":"Total Goles","seleccion":"Over 1.5","cuota_betano":1.25,"razon_cuantitativa":"Razón concisa."}},
  "pick_mas_seguro": {{"partido":"Eq C vs Eq D","categoria_permitida":"Doble Oportunidad","seleccion":"1X","cuota_betano":1.18,"razon_cuantitativa":"Justificación."}},
  "estrategias": [
    {{"tipo":"segura","cuota_total":1.35,"descripcion":"Proteger capital.","picks":["Eq A vs Eq B: Over 1.5 (@1.25)"]}},
    {{"tipo":"moderada","cuota_total":2.20,"descripcion":"Multiplicador óptimo.","picks":["Pick1 (@1.25)","Pick2 (@1.30)","Pick3 (@1.35)"]}},
    {{"tipo":"arriesgada","cuota_total":4.50,"descripcion":"Maximizar ganancias.","picks":["Pick1 (@1.30)","Pick2 (@1.40)","Pick3 (@1.35)","Pick4 (@1.25)"]}}
  ]
}}"""
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash-lite", contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=4096, temperature=0.1, response_mime_type="application/json"
            )
        )
        raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e: return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["⚡ Armador de Boletos", "📊 Base & Stats"])

# ───────────────────────────────────────────────────────────────
# TAB 1 — ARMADOR DE BOLETOS
# ───────────────────────────────────────────────────────────────
with tab1:
    st.markdown(
        "<p style='color:#8A97B5;font-size:12px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.6px;margin-bottom:18px;'>🌍 Mercado: Copa del Mundo 2026 · "
        "Selecciona los partidos a analizar</p>",
        unsafe_allow_html=True,
    )

    with st.spinner("Sincronizando cuotas globales..."):
        datos_api = obtener_partidos_mundial(api_odds)

    if isinstance(datos_api, dict) and "error" in datos_api:
        st.error(f"❌ Error en la API de cuotas: {datos_api['error']}")
    elif not datos_api:
        st.info("⏳ No hay partidos disponibles en este momento. Inténtalo más tarde.")
    else:
        # ── Agrupar por fecha (hora local Chile) ─────────────
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
                f'<div class="date-cnt">{n} partido{"s" if n > 1 else ""}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            for p in partidos_dia:
                h2h  = extraer_h2h(p)
                home = p["home_team"]
                away = p["away_team"]
                hora = fmt_hora(p["commence_time"])



                # ── Barras de probabilidad (HTML inline, sin sangría) ──
                # compact() colapsa todo a una línea → evita el bug del parser Markdown
                if h2h:
                    pw, dw, aw = h2h["home"], h2h["draw"], h2h["away"]
                    ho, do_, ao = h2h["home_odd"], h2h["draw_odd"], h2h["away_odd"]
                    prob_html = (
                        '<div class="prob-wrap">'
                        '<div class="prob-labels">'
                        f'<span>{tr(home)}</span><span>Empate</span><span>{tr(away)}</span>'
                        '</div>'
                        '<div class="prob-bar">'
                        f'<div class="pb-h" style="width:{pw}%"></div>'
                        f'<div class="pb-d" style="width:{dw}%"></div>'
                        f'<div class="pb-a" style="width:{aw}%"></div>'
                        '</div>'
                        '<div class="prob-pcts">'
                        f'<span class="pct-h">{pw}%</span>'
                        f'<span class="pct-d">{dw}%</span>'
                        f'<span class="pct-a">{aw}%</span>'
                        '</div>'
                        '</div>'
                    )
                    c_home = f"@{ho:.2f}"
                    c_draw = f"@{do_:.2f}" if do_ else ""
                    c_away = f"@{ao:.2f}"
                else:
                    prob_html = ""
                    c_home = c_draw = c_away = ""

                # ── Tarjeta del partido (todo en una sola línea) ─────────────
                t_home = (
                    '<div class="team-blk">'
                    f'<div class="t-flag">{fl(home)}</div>'
                    f'<div class="t-name">{tr(home)}</div>'
                    + (f'<div class="t-cuota">{c_home}</div>' if c_home else '')
                    + '</div>'
                )
                t_center = (
                    '<div class="center-blk">'
                    f'<div class="mc-time">{hora}</div>'
                    '<div class="mc-vs">VS</div>'
                    + (f'<div class="mc-draw">{c_draw}</div>' if c_draw else '')
                    + '</div>'
                )
                t_away = (
                    '<div class="team-blk">'
                    f'<div class="t-flag">{fl(away)}</div>'
                    f'<div class="t-name">{tr(away)}</div>'
                    + (f'<div class="t-cuota">{c_away}</div>' if c_away else '')
                    + '</div>'
                )
                st.markdown(
                    '<div class="mcard">'
                    '<div class="teams-row">' + t_home + t_center + t_away + '</div>'
                    + prob_html + '</div>',
                    unsafe_allow_html=True,
                )

                # ── Footer de selección (con clase wrapper) ─
                st.markdown('<div class="mcard-footer">', unsafe_allow_html=True)
                sel = st.checkbox(
                    f"📌 Añadir al análisis — {tr(home)} vs {tr(away)}",
                    key=p["id"],
                )
                st.markdown("</div>", unsafe_allow_html=True)

                if sel:
                    partidos_activos.append(p)

        # ── Botón de construcción de boletos ─────────────────
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        n_sel = len(partidos_activos)
        btn_txt = (
            f"🚀 Construir Boletos · {n_sel} partido{'s' if n_sel != 1 else ''} seleccionado{'s' if n_sel != 1 else ''}"
            if n_sel else "🚀 Construir Boletos"
        )
        if st.button(btn_txt):
            if not partidos_activos:
                st.warning("⚠️ Selecciona al menos un partido para continuar.")
            else:
                with st.spinner("🤖 Calculando combinaciones de alta probabilidad..."):
                    res = ejecutar_algoritmo_quant(api_gemini, partidos_activos)
                if "error" in res:
                    st.error(f"❌ Fallo en el motor de IA: {res['error']}")
                else:
                    st.session_state.ultimo_analisis = res
                    st.session_state.partidos_analizados = " | ".join(
                        [f"{p['home_team']} vs {p['away_team']}" for p in partidos_activos]
                    )
                    st.session_state.ticket_guardado = False

        # ── Mostrar boletos generados ─────────────────────────
        if "ultimo_analisis" in st.session_state:
            data = st.session_state.ultimo_analisis

            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            st.markdown(
                "<p style='color:#EEF4FF;font-weight:800;font-size:13px;"
                "text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;'>🎟️ Boletos Generados</p>",
                unsafe_allow_html=True,
            )
            if data.get("game_script"):
                st.markdown(
                    f"<p style='font-size:12px;color:#8A97B5;margin-bottom:18px;"
                    f"font-style:italic;line-height:1.6;'>💡 {tr_pick(data['game_script'])}</p>",
                    unsafe_allow_html=True,
                )

            def render_slip(clase, titulo, cuota, picks_html, desc):
                st.markdown(
                    f'<div class="tslip {clase}">'
                    f'<div class="slip-hdr">'
                    f'<span class="slip-tit">{titulo}</span>'
                    f'<span class="slip-q">@{cuota}</span>'
                    f'</div>'
                    + picks_html +
                    f'<div class="slip-desc"><b>Veredicto:</b> {tr_pick(desc)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Pick Estrella
            pe = data.get("pick_estrella", {})
            render_slip(
                "slip-base", "⭐ Pick Base (Single)", pe.get("cuota_betano", "-"),
                f'<div class="i-match">{tr_pick(pe.get("partido", ""))}</div>'
                f'<div class="i-bet">{tr_pick(pe.get("seleccion", ""))}</div>',
                pe.get("razon_cuantitativa", ""),
            )

            # Pick Anti-Sorpresas
            ps = data.get("pick_mas_seguro", {})
            render_slip(
                "slip-anti", "🛡️ Pick Anti-Sorpresas", ps.get("cuota_betano", "-"),
                f'<div class="i-match">{tr_pick(ps.get("partido", ""))}</div>'
                f'<div class="i-bet">{tr_pick(ps.get("seleccion", ""))}</div>',
                ps.get("razon_cuantitativa", ""),
            )

            # Estrategias
            estrat_map = {
                "segura":     ("slip-segura",     "🟢 COMBINADA SEGURA"),
                "moderada":   ("slip-moderada",   "🟡 COMBINADA MODERADA"),
                "arriesgada": ("slip-arriesgada", "🔴 COMBINADA ARRIESGADA"),
            }
            for e in data.get("estrategias", []):
                clase, tit = estrat_map.get(e.get("tipo", "segura"), ("slip-segura", "Combinada"))
                picks_html = ""
                for pick in e.get("picks", []):
                    if ":" in pick:
                        p_str, b_str = pick.split(":", 1)
                    else:
                        p_str, b_str = "Partido", pick
                    picks_html += (
                        f'<div class="i-match">{tr_pick(p_str.strip())}</div>'
                        f'<div class="i-bet">{tr_pick(b_str.strip())}</div>'
                    )
                render_slip(clase, tit, e.get("cuota_total", "-"), picks_html, e.get("descripcion", ""))

            # Botón guardar
            if not st.session_state.get("ticket_guardado", False):
                st.markdown('<div class="btn-save">', unsafe_allow_html=True)
                if st.button("💾 Guardar Boletos en Base de Datos"):
                    if guardar_ticket_db("Mundial 2026", st.session_state.partidos_analizados, data):
                        st.session_state.ticket_guardado = True
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.success("✅ Boletos guardados permanentemente en la Base de Datos.")

# ───────────────────────────────────────────────────────────────
# TAB 2 — BASE & STATS
# ───────────────────────────────────────────────────────────────
with tab2:
    with st.spinner("🤖 Evaluando resultados en vivo..."):
        auto_verificar_jornada()
        historial = cargar_historial_db()

    # ── Dashboard de estadísticas ─────────────────────────────
    acertados = fallidos = 0
    if historial:
        for t in historial:
            for col in ["res_estrella", "res_mas_seguro", "res_segura", "res_moderada", "res_arriesgada"]:
                v = t.get(col)
                if v == "acertado":  acertados += 1
                elif v == "fallido": fallidos  += 1

    total    = acertados + fallidos
    hit      = int(acertados / total * 100) if total > 0 else 0
    color_hr = "#00E676" if hit >= 50 else "#FFB700" if hit >= 30 else "#FF3B5C"

    st.markdown(
        '<div class="dash-grid">'
        '<div class="d-card">'
        f'<div class="d-val" style="color:{color_hr};">{hit}%</div>'
        '<div class="d-lbl">Hit Rate Global</div>'
        '</div>'
        '<div class="d-card">'
        f'<div class="d-val" style="color:#00E676;">{acertados}</div>'
        '<div class="d-lbl">Picks Acertados</div>'
        '</div>'
        '<div class="d-card">'
        f'<div class="d-val" style="color:#FF3B5C;">{fallidos}</div>'
        '<div class="d-lbl">Picks Fallados</div>'
        '</div>'
        '</div>'
        "<p style='color:#EEF4FF;font-weight:800;font-size:13px;text-transform:uppercase;"
        "letter-spacing:.5px;margin-bottom:16px;'>📋 Historial de Operaciones</p>",
        unsafe_allow_html=True,
    )

    if not historial:
        st.info("No hay registros. Guarda tus primeros boletos en la pestaña anterior.")
    else:
        for t in historial:
            data_t     = json.loads(t["analisis_json"])
            estrategias = data_t.get("estrategias", [])

            with st.expander(f"🎫 {t['fecha_gen']} · {t['liga']}"):
                st.markdown(
                    f"<div style='font-size:10px;color:#8A97B5;margin-bottom:12px;'>"
                    f"<b>Partidos:</b> {tr_pick(t['partidos'])}</div>",
                    unsafe_allow_html=True,
                )

                items = [
                    ("res_estrella",   "⭐ Pick Base",
                     tr_pick(data_t.get("pick_estrella", {}).get("seleccion", "N/D"))),
                    ("res_mas_seguro", "🛡️ Anti-Sorpresas",
                     tr_pick(data_t.get("pick_mas_seguro", {}).get("seleccion", "N/D"))),
                    ("res_segura",     "🟢 Combinada Segura",
                     f"Cuota @{estrategias[0].get('cuota_total','N/D')}" if len(estrategias) > 0 else "N/D"),
                    ("res_moderada",   "🟡 Combinada Moderada",
                     f"Cuota @{estrategias[1].get('cuota_total','N/D')}" if len(estrategias) > 1 else "N/D"),
                    ("res_arriesgada", "🔴 Combinada Arriesgada",
                     f"Cuota @{estrategias[2].get('cuota_total','N/D')}" if len(estrategias) > 2 else "N/D"),
                ]

                for col_name, titulo, sel_txt in items:
                    estado = t.get(col_name, "pendiente")
                    bg = "#00E676" if estado == "acertado" else "#FF3B5C" if estado == "fallido" else "#4A5568"
                    st.markdown(
                        f'<div class="hist-row" style="border-left-color:{bg};">'
                        f'<div><div class="h-meta">{titulo}</div>'
                        f'<div class="h-txt">{sel_txt}</div></div>'
                        f'<span class="h-badge" style="background:{bg};color:#fff;">{estado}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    c1, c2, c3, _ = st.columns([1, 1, 1, 3])
                    if c1.button("✅", key=f"ok_{t['id']}_{col_name}", help="Marcar como Acertado"):
                        actualizar_resultado_manual(t["id"], col_name, "acertado"); st.rerun()
                    if c2.button("❌", key=f"fa_{t['id']}_{col_name}", help="Marcar como Fallido"):
                        actualizar_resultado_manual(t["id"], col_name, "fallido"); st.rerun()
                    if c3.button("⏳", key=f"pe_{t['id']}_{col_name}", help="Restablecer a Pendiente"):
                        actualizar_resultado_manual(t["id"], col_name, "pendiente"); st.rerun()

                st.markdown("<hr style='border-color:rgba(255,255,255,0.05);margin:10px 0;'>", unsafe_allow_html=True)
                if st.button("🗑️ Eliminar Registro", key=f"del_{t['id']}"):
                    eliminar_ticket_db(t["id"]); st.rerun()
