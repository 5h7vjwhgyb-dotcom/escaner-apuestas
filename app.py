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

def fmt_fecha(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt.weekday()]} {dt.day} {meses[dt.month]} · {dt.strftime('%H:%M')} UTC"
    except: return "Fecha no disponible"

def render_card(partido, idx=1):
    home  = partido.get("home_team","Local")
    away  = partido.get("away_team","Visita")
    fecha = fmt_fecha(partido.get("commence_time",""))
    liga_title = partido.get("sport_title","Fútbol")

    h2h, t_over, t_under = extraer_odds(partido)
    probs = calcular_probs(h2h)
    apuesta = mejor_apuesta(h2h, probs, t_over, t_under)

    h_odds = h2h["home"] or "—"
    d_odds = h2h["draw"] or "—"
    a_odds = h2h["away"] or "—"

    # ── Over/Under rows ──────────────────────────────
    ou_rows = ""
    for pt in sorted(t_over.keys()):
        if pt in t_under:
            total = (1/t_over[pt]) + (1/t_under[pt])
            op = round((1/t_over[pt])/total*100)
            up = round((1/t_under[pt])/total*100)
            ou_rows += f"""
            <div style="display:flex;gap:6px;margin-bottom:5px;">
              <div style="flex:1;background:#0d1117;border-radius:7px;padding:7px 4px;text-align:center;">
                <div style="color:#22c55e;font-size:10px;font-weight:700;">O {pt}</div>
                <div style="color:#e1e1e1;font-size:16px;font-weight:700;">{t_over[pt]}</div>
                <div style="color:#6b7280;font-size:10px;">{op}%</div>
              </div>
              <div style="flex:1;background:#0d1117;border-radius:7px;padding:7px 4px;text-align:center;">
                <div style="color:#ef4444;font-size:10px;font-weight:700;">U {pt}</div>
                <div style="color:#e1e1e1;font-size:16px;font-weight:700;">{t_under[pt]}</div>
                <div style="color:#6b7280;font-size:10px;">{up}%</div>
              </div>
            </div>"""

    ou_section = f"""
    <div style="background:#1a2235;border-radius:10px;padding:11px;margin-bottom:12px;">
      <div style="color:#6b7280;font-size:10px;letter-spacing:1.2px;font-weight:700;margin-bottom:7px;">OVER / UNDER</div>
      {ou_rows or '<span style="color:#6b7280;font-size:12px;">No disponible en esta liga</span>'}
    </div>""" if t_over else ""

    # ── Apuesta sugerida ─────────────────────────────
    bet_html = ""
    if apuesta:
        bet_html = f"""
    <div style="background:rgba(0,230,118,0.07);border:1px solid #00e676;border-radius:10px;
                padding:11px 13px;display:flex;justify-content:space-between;
                align-items:center;margin-bottom:13px;">
      <div>
        <div style="color:#6b7280;font-size:10px;letter-spacing:1px;font-weight:700;">🛡️ APUESTA SUGERIDA</div>
        <div style="color:#00e676;font-size:14px;font-weight:700;margin-top:2px;">{apuesta['label']}</div>
      </div>
      <div style="text-align:right;">
        <div style="color:#6b7280;font-size:10px;">Prob: {apuesta['prob']}%</div>
        <div style="color:#00e676;font-size:18px;font-weight:900;">@{apuesta['odds']}</div>
      </div>
    </div>"""

    # ── Prob bar ─────────────────────────────────────
    hp, dp, ap = probs["home"], probs["draw"], probs["away"]

    return f"""
<div style="background:#161c2b;border-radius:18px;padding:17px;border:1px solid #2a3349;
            margin-bottom:18px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

  <!-- Header -->
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
    <span style="color:#8b949e;font-size:12px;">📅 {fecha}</span>
    <span style="background:#2d3748;color:#e1e1e1;font-size:10px;padding:2px 9px;border-radius:20px;font-weight:700;">M {idx}</span>
  </div>
  <div style="color:#6b7280;font-size:11px;margin-bottom:14px;">📍 {liga_title}</div>

  <!-- Teams -->
  <div style="display:flex;align-items:center;margin-bottom:15px;">
    <div style="flex:2;text-align:center;">
      <div style="font-size:44px;line-height:1.1;">{flag(home)}</div>
      <div style="color:#e1e1e1;font-weight:700;font-size:14px;margin-top:5px;">{home}</div>
      <div style="color:#f59e0b;font-size:12px;">{estrellas(hp)}</div>
    </div>
    <div style="flex:1;text-align:center;">
      <div style="color:#6b7280;font-size:20px;font-weight:900;letter-spacing:3px;">— : —</div>
      <div style="background:#2d3748;color:#8b949e;font-size:9px;padding:3px 8px;
                  border-radius:10px;margin-top:6px;display:inline-block;letter-spacing:.5px;">Cuotas 1X2</div>
    </div>
    <div style="flex:2;text-align:center;">
      <div style="font-size:44px;line-height:1.1;">{flag(away)}</div>
      <div style="color:#e1e1e1;font-weight:700;font-size:14px;margin-top:5px;">{away}</div>
      <div style="color:#f59e0b;font-size:12px;">{estrellas(ap)}</div>
    </div>
  </div>

  <!-- Odds boxes -->
  <div style="display:flex;gap:6px;margin-bottom:13px;">
    <div style="flex:1;background:#1a2235;border-radius:10px;padding:10px 4px;text-align:center;">
      <div style="color:#6b7280;font-size:9px;letter-spacing:1px;font-weight:700;">LOCAL [1]</div>
      <div style="color:#e1e1e1;font-size:22px;font-weight:700;line-height:1.2;">{h_odds}</div>
      <div style="color:#6b7280;font-size:10px;">Prob: {hp}%</div>
    </div>
    <div style="flex:1;background:#1a2235;border-radius:10px;padding:10px 4px;text-align:center;">
      <div style="color:#6b7280;font-size:9px;letter-spacing:1px;font-weight:700;">EMPATE [X]</div>
      <div style="color:#e1e1e1;font-size:22px;font-weight:700;line-height:1.2;">{d_odds}</div>
      <div style="color:#6b7280;font-size:10px;">Prob: {dp}%</div>
    </div>
    <div style="flex:1;background:#1a2235;border-radius:10px;padding:10px 4px;text-align:center;">
      <div style="color:#6b7280;font-size:9px;letter-spacing:1px;font-weight:700;">VISITA [2]</div>
      <div style="color:#e1e1e1;font-size:22px;font-weight:700;line-height:1.2;">{a_odds}</div>
      <div style="color:#6b7280;font-size:10px;">Prob: {ap}%</div>
    </div>
  </div>

  {ou_section}
  {bet_html}

  <!-- Probability bar -->
  <div>
    <div style="color:#6b7280;font-size:10px;letter-spacing:1.2px;font-weight:700;margin-bottom:6px;">📈 PROBABILIDAD DE VICTORIA:</div>
    <div style="display:flex;border-radius:8px;overflow:hidden;height:28px;">
      <div style="background:#22c55e;width:{hp}%;display:flex;align-items:center;
                  justify-content:center;color:white;font-size:12px;font-weight:700;min-width:28px;">{hp}%</div>
      <div style="background:#4b5563;width:{dp}%;display:flex;align-items:center;
                  justify-content:center;color:#ddd;font-size:10px;min-width:28px;">EMP</div>
      <div style="background:#ef4444;width:{ap}%;display:flex;align-items:center;
                  justify-content:center;color:white;font-size:12px;font-weight:700;min-width:28px;">{ap}%</div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:10px;color:#6b7280;">
      <span>{home}</span><span>EMPATE</span><span>{away}</span>
    </div>
  </div>
</div>"""

# ═══════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡MUNDIAL", layout="centered",
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

# ─── HEADER ──────────────────────────────────────────────────────
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
    BET<span style="color:#00e676;">⚡</span>MUNDIAL
  </span>
  <span style="border:1px solid {bcol};color:{bcol};font-size:10px;font-weight:700;
               padding:4px 10px;border-radius:20px;letter-spacing:.5px;">{dot} {badge}</span>
</div>
""", unsafe_allow_html=True)

# ─── CONFIGURACIÓN ───────────────────────────────────────────────
with st.expander("⚙️  Configuración — Claves API", expanded=not online):
    c1, c2 = st.columns(2)
    with c1:
        api_gemini = st.text_input("Gemini API Key", type="password",
                                   help="aistudio.google.com", key="_gem")
    with c2:
        api_odds = st.text_input("Odds API Key", type="password",
                                 help="the-odds-api.com", key="_odd")
    st.caption("💡 Tier gratuito Odds API: 500 peticiones/mes · Gemini 3.5 Flash")

# ─── LIGA ────────────────────────────────────────────────────────
liga_label = st.selectbox("🏆 Liga", list(LIGAS.keys()), index=0)
liga = LIGAS[liga_label]

if api_odds:
    if st.button("🔍 Ver ligas con partidos activos ahora"):
        with st.spinner("Consultando..."):
            try:
                r = requests.get(
                    f"https://api.the-odds-api.com/v4/sports/?apiKey={api_odds}&all=false",
                    timeout=10).json()
                futbol = [s for s in r if isinstance(r,list) and
                          s.get("group","").lower()=="soccer"] if isinstance(r,list) else []
                if futbol:
                    st.success("✅ Ligas activas:")
                    for s in futbol:
                        st.code(f"{s['title']}  →  {s['key']}")
                else:
                    st.info("No se encontraron ligas activas o clave inválida.")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")

# ─── CARGA DE PARTIDOS ───────────────────────────────────────────
partido = None

if not api_odds:
    st.info("🔑 Ingresa tu Odds API Key en Configuración para ver partidos.")
else:
    url = (f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
           f"?apiKey={api_odds}&regions=eu&markets=h2h,totals")
    try:
        resp_raw = requests.get(url, timeout=10)
        restantes = resp_raw.headers.get("x-requests-remaining","?")
        resp = resp_raw.json()

        if isinstance(resp, dict) and resp.get("message"):
            st.error(f"❌ Odds API: {resp['message']}")
        elif isinstance(resp, list) and len(resp) > 0:
            lista = {
                f"{p.get('home_team','Local')} vs {p.get('away_team','Visita')}": p
                for p in resp
            }
            partido_nombre = st.selectbox("🎯 Partido", list(lista.keys()))
            partido = lista[partido_nombre]

            # Render beautiful match card
            idx = list(lista.keys()).index(partido_nombre) + 1
            st.markdown(render_card(partido, idx), unsafe_allow_html=True)

            st.markdown(
                f'<div style="color:#6b7280;font-size:10px;text-align:right;'
                f'margin-top:-10px;margin-bottom:10px;">'
                f'📊 Peticiones restantes: <strong style="color:#e1e1e1;">{restantes}</strong>/500</div>',
                unsafe_allow_html=True
            )
        else:
            st.warning("⚠️ No hay partidos disponibles. Prueba con **🌍 Mundial 2026** o **🇺🇸 MLS**.")

    except requests.exceptions.Timeout:
        st.error("❌ Tiempo de espera agotado. Inténtalo de nuevo.")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# ─── CONTEXTO + ANÁLISIS ─────────────────────────────────────────
st.markdown("---")
contexto = st.text_area(
    "📋 Contexto adicional",
    placeholder="Ej: Delantero titular lesionado · Lluvia prevista · Local invicto en casa"
)

if st.button("🚀 Analizar 15 Mercados con IA"):
    if not api_gemini:
        st.error("❌ Falta la Gemini API Key.")
    elif not partido:
        st.error("❌ Selecciona un partido primero.")
    else:
        prompt = f"""
ACTÚA COMO ANALISTA DE APUESTAS DEPORTIVAS. Datos del partido: {partido}
Contexto: {contexto or 'Sin contexto adicional.'}

REGLA CRÍTICA: SI UN DATO NO EXISTE EN LA API → MARCA 'DATO INSUFICIENTE'. PROHIBIDO INVENTAR.

Analiza estos 15 mercados:
1. Ganador (1X2)  2. Doble Oportunidad  3. Ambos Marcan (BTTS)
4. Hándicap Asiático  5. Resultado al Descanso  6. Descanso/Final
7. Marcador Exacto (top 5)  8. Primer Goleador  9. Último Goleador
10. Total Córners  11. Total Tarjetas  12. Quién Marca Primero
13. Portería a Cero  14. Remates al Arco
15. TABLA Over/Under: 0.5 / 1.5 / 2.5 / 3.5 / 4.5 / 5.5

FORMATO por mercado:
### [N]. [Mercado]
- Selección: [valor]
- Cuota: [valor o DATO INSUFICIENTE]
- Confianza: [Alta/Media/Baja]
- Motivo: [máx 8 palabras]
"""
        with st.spinner("🔍 Analizando con Gemini 3.5 Flash..."):
            try:
                client = genai.Client(api_key=api_gemini)
                resp = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.25)
                )
                texto = resp.text
                st.markdown("### 🔥 Análisis — 15 Mercados")
                for sec in texto.split("###"):
                    if sec.strip():
                        st.markdown(
                            f'<div class="result-card">{sec.strip()}</div>',
                            unsafe_allow_html=True
                        )
                st.success("✅ Análisis completado.")
            except Exception as e:
                st.error(f"❌ Error Gemini: {e}")

st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
