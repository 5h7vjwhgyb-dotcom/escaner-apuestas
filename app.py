import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime
import math

# ═══════════════════════════════════════════════
# BANDERAS
# ═══════════════════════════════════════════════
BANDERAS = {
    "Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷",
    "Czechia":"🇨🇿","Czech Republic":"🇨🇿","USA":"🇺🇸",
    "United States":"🇺🇸","Paraguay":"🇵🇾","Canada":"🇨🇦",
    "Bosnia and Herzegovina":"🇧🇦","Qatar":"🇶🇦","Switzerland":"🇨🇭",
    "Australia":"🇦🇺","Turkey":"🇹🇷","Turkiye":"🇹🇷",
    "Germany":"🇩🇪","Curacao":"🇨🇼","Ivory Coast":"🇨🇮",
    "Ecuador":"🇪🇨","Brazil":"🇧🇷","Morocco":"🇲🇦","Haiti":"🇭🇹",
    "Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Spain":"🇪🇸","Cabo Verde":"🇨🇻",
    "Saudi Arabia":"🇸🇦","Argentina":"🇦🇷","Croatia":"🇭🇷",
    "New Zealand":"🇳🇿","Senegal":"🇸🇳","France":"🇫🇷",
    "Japan":"🇯🇵","Colombia":"🇨🇴","Portugal":"🇵🇹",
    "DR Congo":"🇨🇩","Congo DR":"🇨🇩","Uzbekistan":"🇺🇿",
    "England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Netherlands":"🇳🇱","Belgium":"🇧🇪",
    "Nigeria":"🇳🇬","Cameroon":"🇨🇲","Ghana":"🇬🇭",
    "Uruguay":"🇺🇾","Chile":"🇨🇱","Peru":"🇵🇪",
    "Venezuela":"🇻🇪","Iran":"🇮🇷","Serbia":"🇷🇸",
    "Denmark":"🇩🇰","Poland":"🇵🇱","Sweden":"🇸🇪",
    "Norway":"🇳🇴","Ukraine":"🇺🇦","Wales":"🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Algeria":"🇩🇿","Egypt":"🇪🇬","Tunisia":"🇹🇳",
    "Costa Rica":"🇨🇷","Panama":"🇵🇦","Honduras":"🇭🇳",
    "Jamaica":"🇯🇲","UAE":"🇦🇪","Iraq":"🇮🇶",
    "China":"🇨🇳","Indonesia":"🇮🇩","Greece":"🇬🇷",
    "Romania":"🇷🇴","Hungary":"🇭🇺","Slovakia":"🇸🇰",
    "Slovenia":"🇸🇮","Austria":"🇦🇹","Finland":"🇫🇮",
    "Ireland":"🇮🇪","New Caledonia":"🇳🇨",
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
# HELPERS
# ═══════════════════════════════════════════════
def flag(team): return BANDERAS.get(team, "🏳️")

def estrellas(prob):
    if prob >= 62: return "★★★★★"
    if prob >= 52: return "★★★★☆"
    if prob >= 35: return "★★★☆☆"
    if prob >= 22: return "★★☆☆☆"
    return "★☆☆☆☆"

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
    away_p = 100 - home_p - draw_p   # ensure exact 100
    return {"home": home_p, "draw": draw_p, "away": away_p}

def mejor_apuesta(h2h, probs, t_over, t_under):
    cands = []
    for pt in sorted(t_over.keys()):
        if pt in t_under:
            total = (1/t_over[pt]) + (1/t_under[pt])
            cands.append({"label": f"Más de {pt} Goles",  "odds": t_over[pt],  "prob": round((1/t_over[pt])/total*100)})
            cands.append({"label": f"Menos de {pt} Goles","odds": t_under[pt], "prob": round((1/t_under[pt])/total*100)})
    for k, lbl in [("home","Victoria Local"),("draw","Empate"),("away","Victoria Visitante")]:
        if h2h[k]: cands.append({"label":lbl,"odds":h2h[k],"prob":probs[k]})
    return max(cands, key=lambda x: x["prob"]) if cands else None

def fmt_fecha(iso, simple=False):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        if simple: return dt.strftime('%Y-%m-%d')
        dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt.weekday()]} {dt.day} {meses[dt.month]} · {dt.strftime('%H:%M')} UTC"
    except: return "Fecha no disponible"

def render_simplified_card(partido, idx=1):
    home  = partido.get("home_team","Local")
    away  = partido.get("away_team","Visita")
    fecha = fmt_fecha(partido.get("commence_time",""))
    h2h, t_over, t_under = extraer_odds(partido)
    probs = calcular_probs(h2h)
    
    # ── Probability bar ─────────────────────────────────────
    hp, dp, ap = probs["home"], probs["draw"], probs["away"]

    return f"""
<div style="background:#161c2b;border-radius:12px;padding:12px;border:1px solid #2a3349;
            margin-bottom:12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
    <span style="color:#8b949e;font-size:11px;">📅 {fecha}</span>
    <span style="background:#2d3748;color:#e1e1e1;font-size:9px;padding:2px 7px;border-radius:20px;font-weight:700;">M {idx}</span>
  </div>

  <div style="display:flex;align-items:center;margin-bottom:10px;">
    <div style="flex:2;text-align:center;">
      <div style="font-size:32px;line-height:1.1;">{flag(home)}</div>
      <div style="color:#e1e1e1;font-weight:700;font-size:12px;margin-top:4px;">{home}</div>
      <div style="color:#f59e0b;font-size:10px;">{estrellas(hp)}</div>
    </div>
    <div style="flex:1;text-align:center;">
      <div style="color:#6b7280;font-size:16px;font-weight:900;">— : —</div>
    </div>
    <div style="flex:2;text-align:center;">
      <div style="font-size:32px;line-height:1.1;">{flag(away)}</div>
      <div style="color:#e1e1e1;font-weight:700;font-size:12px;margin-top:4px;">{away}</div>
      <div style="color:#f59e0b;font-size:10px;">{estrellas(ap)}</div>
    </div>
  </div>

  <div style="display:flex;border-radius:6px;overflow:hidden;height:18px;">
    <div style="background:#22c55e;width:{hp}%;display:flex;align-items:center;
                justify-content:center;color:white;font-size:10px;font-weight:700;min-width:18px;">{hp}%</div>
    <div style="background:#4b5563;width:{dp}%;display:flex;align-items:center;
                justify-content:center;color:#ddd;font-size:8px;min-width:18px;">EMP</div>
    <div style="background:#ef4444;width:{ap}%;display:flex;align-items:center;
                justify-content:center;color:white;font-size:10px;font-weight:700;min-width:18px;">{ap}%</div>
  </div>
</div>"""

# ═══════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡COMBINADAS", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
  [data-testid="stAppViewContainer"]  { background:#0d1117 !important; }
  [data-testid="stHeader"]            { background:transparent !important; }
  [data-testid="stDecoration"]        { display:none; }
  [data-testid="stToolbar"]           { display:none; }
  section[data-testid="stSidebar"]    { display:none; }
  .block-container { padding-top:0.8rem !important; max-width:520px !important; }

  /* Text & labels */
  label, .stTextInput label, .stTextArea label,
  .stSelectbox label { color:#8b949e !important; font-size:12px !important; }
  .stTextInput input, .stTextArea textarea {
    background:#161c2b !important; color:#e1e1e1 !important;
    border:1px solid #2d3748 !important; border-radius:10px !important;
    font-size:13px !important;
  }
  /* Selectbox */
  [data-testid="stSelectbox"] > div > div {
    background:#161c2b !important; border:1px solid #2d3748 !important;
    border-radius:10px !important; color:#e1e1e1 !important;
  }
  /* Expander */
  [data-testid="stExpander"] {
    background:#161c2b !important; border:1px solid #2d3748 !important;
    border-radius:12px !important;
  }
  [data-testid="stExpanderToggleIcon"] svg { fill:#00e676 !important; }

  /* Buttons */
  .stButton > button {
    background:linear-gradient(90deg,#00e676,#00b4d8) !important;
    border:none !important; border-radius:12px !important;
    color:#0d1117 !important; font-weight:800 !important;
    font-size:14px !important; width:100% !important;
    padding:0.65em !important; letter-spacing:.4px !important;
  }
  .stButton > button:hover { opacity:.9; }

  /* Warning/info/error */
  [data-testid="stAlert"] { border-radius:12px !important; }

  /* Divider */
  hr { border-color:#2d3748 !important; }

  /* Results card */
  .result-card {
    background:#161c2b; border-left:4px solid #00e676;
    border-radius:12px; padding:16px; margin-bottom:14px;
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

# ─── CONFIGURACIÓN (Vuelven las casillas de texto) ───────────────
with st.expander("⚙️  Configuración — Claves API", expanded=not online):
    c1, c2 = st.columns(2)
    with c1:
        api_gemini = st.text_input("Gemini API Key", type="password",
                                   help="aistudio.google.com", key="_gem")
    with c2:
        api_odds = st.text_input("Odds API Key", type="password",
                                 help="the-odds-api.com", key="_odd")
    st.caption("💡 Tier gratuito Odds API: 500 peticiones/mes · Gemini 3.5 Flash")

# ─── LIGA Y AUTO-LOAD PARTIDOS (Próximos 6) ──────────────────────
liga_label = st.selectbox("🏆 Liga para buscar próximos partidos", list(LIGAS.keys()), index=0)
liga = LIGAS[liga_label]

upcoming_matches = []
upcoming_matches_dict = {}
restantes = "?"

if api_odds:
    url = (f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
           f"?apiKey={api_odds}&regions=eu&markets=h2h,totals")
    
    with st.spinner(f"🚀 Buscando próximos partidos..."):
        try:
            resp_raw = requests.get(url, timeout=10)
            restantes = resp_raw.headers.get("x-requests-remaining","?")
            resp = resp_raw.json()

            if isinstance(resp, list) and len(resp) > 0:
                # Ordenar por fecha del partido
                sorted_resp = sorted(resp, key=lambda x: x.get('commence_time', ''))
                
                # Agarrar los primeros 6
                upcoming_matches = sorted_resp[:6]
                for p in upcoming_matches:
                    name = f"{fmt_fecha(p['commence_time'], simple=True)}: {p['home_team']} vs {p['away_team']}"
                    upcoming_matches_dict[name] = p
            elif isinstance(resp, dict) and resp.get("message"):
                 st.error(f"❌ Odds API Error: {resp['message']}")
            else:
                 st.warning("⚠️ No se encontraron próximos partidos para esta liga.")
        except Exception as e:
            st.error(f"❌ Error al cargar partidos: {e}")

st.markdown("---")

# ─── SELECCIÓN DE PARTIDOS ─────────────────────────────────────
st.subheader("🎯 Selecciona de los próximos 6 partidos")

if upcoming_matches_dict:
    selected_match_names = st.multiselect(
        "Selecciona hasta 6 partidos",
        options=list(upcoming_matches_dict.keys()),
        default=None,
        help="Selecciona los partidos que quieres analizar para generar las apuestas combinadas."
    )
    
    selected_matches = [upcoming_matches_dict[name] for name in selected_match_names]

    # Mostrar tarjetas simples para los partidos seleccionados
    if selected_matches:
        st.markdown("### 👀 Vista previa de selección")
        for i, p in enumerate(selected_matches):
            st.markdown(render_simplified_card(p, i+1), unsafe_allow_html=True)
            
        st.markdown(
            f'<div style="color:#6b7280;font-size:10px;text-align:right;'
            f'margin-top:-10px;margin-bottom:10px;">'
            f'📊 Peticiones Odds restantes: <strong style="color:#e1e1e1;">{restantes}</strong>/500</div>',
            unsafe_allow_html=True
        )
else:
    selected_matches = []
    st.info("Ingresa tus claves API arriba para ver los próximos partidos disponibles.")

# ─── CONTEXTO + ANÁLISIS COMBINADO ──────────────────────────────
st.markdown("---")
contexto = st.text_area(
    "📋 Contexto adicional (opcional)",
    placeholder="Ej: Si quieres darle información a la IA sobre bajas de jugadores en estos partidos..."
)

if st.button("🚀 Generar Estrategias (Segura/Media/Arriesgada)"):
    if not api_gemini:
        st.error("❌ Falta la Gemini API Key. Ponla en Configuración.")
    elif not selected_matches:
        st.error("❌ Selecciona al menos un partido de la lista de arriba primero.")
    else:
        # Extraer cuotas y mercado para el prompt
        formatted_matches = []
        for p in selected_matches:
            h2h, t_over, t_under = extraer_odds(p)
            probs = calcular_probs(h2h)
            best = mejor_apuesta(h2h, probs, t_over, t_under)
            
            p_data = {
                "local": p['home_team'],
                "visita": p['away_team'],
                "fecha": fmt_fecha(p['commence_time'], simple=True),
                "probabilidades": probs,
                "mejor_apuesta_individual": best,
                "cuotas_1x2": h2h,
                "goles_over": t_over,
                "goles_under": t_under
            }
            formatted_matches.append(p_data)

        prompt = f"""
ACTÚA COMO ANALISTA DE APUESTAS DEPORTIVAS experto.
Datos de los partidos seleccionados (en formato JSON para precisión, extraídos de los mercados 1X2 y Totales Over/Under):
{formatted_matches}

Contexto (aplica a todos los partidos relevantes): {contexto or 'Sin contexto adicional.'}

TU TAREA es generar EXACTAMENTE tres estrategias de apuestas detalladas a continuación basadas ÚNICAMENTE en las cuotas dadas.
PROHIBIDO: Inventar datos. Si una estrategia solicitada es imposible con los datos proporcionados, marca 'DATO INSUFICIENTE'.

## 1. Apuesta Segura
- Objetivo: Crear de 1 a 2 apuestas (picks) del *mismo* partido individual (de los que te pasé) con la probabilidad de éxito absoluta MÁS ALTA.
- Formato:
  - Partido: [Partido: Local vs Visita]
  - Pick 1: [valor], Probabilidad calculada: [valor]%, Cuota: @[valor], Motivo: [max 15 palabras]
  - Pick 2 (opcional): [valor], Probabilidad calculada: [valor]%, Cuota: @[valor], Motivo: [max 15 palabras]

## 2. Apuesta de Riesgo Medio (Combinada/Parlay)
- Objetivo: Crear una combinada (parlay) mezclando de 3 a 5 apuestas (picks) de partidos *diferentes* (de la lista de seleccionados) pero que se jueguen el *mismo* día calendario. Prioriza las probabilidades más altas.
- Formato:
  - Detalles Combinada: Cuota Total aprox. @[multiplica las cuotas]
  - [Partido 1: Local vs Visita]: [Pick], Prob: [valor]%, Cuota: @[valor], Motivo: [max 10 palabras]
  - [Partido 2: Local vs Visita]: [Pick], Prob: [valor]%, Cuota: @[valor], Motivo: [max 10 palabras]
  - ... repetir para todos los picks.

## 3. Apuesta Arriesgada (Combinada/Parlay Larga)
- Objetivo: Crear una combinada más grande de 5 a 7 apuestas (picks) de partidos *diferentes* (de la lista) del *mismo* día calendario. Trata de buscar buenas cuotas pero que sigan siendo probables.
- Formato:
  - Detalles Combinada: Cuota Total aprox. @[multiplica las cuotas]
  - [Partido 1]: [Pick], Prob: [valor]%, Cuota: @[valor], Motivo: [max 10 palabras]
  - ... repetir para todos los picks.
"""
        with st.spinner("🔍 Analizando combinaciones con IA..."):
            try:
                client = genai.Client(api_key=api_gemini)
                resp = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.2)
                )
                texto = resp.text
                st.markdown("### 🔥 Resultados de tus Estrategias")
                
                # Render results in cleaner cards
                for sec in texto.split("##"):
                    if sec.strip():
                        # Extract header for title and content for the card
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
                st.success("✅ Análisis completado.")
            except Exception as e:
                st.error(f"❌ Error al consultar IA: {e}")

st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
