```python
import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
import json
from supabase import create_client, Client

# Configuración de zona horaria (Chile)
try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-4))

# ═══════════════════════════════════════════════════════════════
# 1. ESTILOS VISUALES PREMIUM (Tickets y Dashboard)
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡COMBINADAS", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background:#07101E !important; color:#EEF4FF !important; font-family:'Inter', sans-serif !important; }
  [data-testid="stHeader"] { background:transparent !important; }
  .block-container { padding-top:1rem !important; max-width:650px !important; }
  
  /* Encabezado */
  .hdr { display:flex; align-items:center; justify-content:space-between; padding:16px 20px; background:#0E1A2C; border:1px solid rgba(255,255,255,.06); border-radius:12px; margin-bottom:20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  .logo { font-size:20px; font-weight:800; letter-spacing:-0.5px; }
  .logo-bolt { color:#00C2FF; }
  .badge-betano { background:rgba(255,107,0,.15); border:1px solid rgba(255,107,0,.3); padding:5px 12px; border-radius:20px; font-size:10px; font-weight:800; color:#FF6B00; text-transform:uppercase; }
  
  /* Botones Principales */
  .stButton>button { background:linear-gradient(135deg,#00C2FF,#0091CC) !important; border:none !important; border-radius:8px !important; color:#fff !important; font-weight:800 !important; font-size:14px !important; width:100% !important; padding:0.8em !important; transition: all 0.2s; }
  .stButton>button:hover { opacity:0.9; transform: translateY(-1px); }
  .btn-guardar>button { background:linear-gradient(135deg,#8B5CF6,#6D28D9) !important; margin-top:10px !important; }
  
  /* Cajas de selección */
  [data-testid="stCheckbox"] { background:#131F30; padding:12px 15px; border-radius:8px; border:1px solid rgba(255,255,255,.06); margin-bottom:8px; }
  
  /* -------------------------------------
     DISEÑO DE BOLETOS DE APUESTA (SLIPS) 
     ------------------------------------- */
  .ticket-slip { background:#111B29; border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:18px; margin-bottom:16px; position:relative; overflow:hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
  .ticket-slip::before { content:''; position:absolute; top:0; left:0; width:5px; height:100%; }
  
  /* Colores por estrategia */
  .slip-base::before { background:#00C2FF; } /* Pick Base */
  .slip-anti::before { background:#8B5CF6; } /* Anti-Sorpresas */
  .slip-segura::before { background:#00E676; } /* Combinada Segura */
  .slip-moderada::before { background:#FFB700; } /* Combinada Moderada */
  .slip-arriesgada::before { background:#FF3B5C; } /* Combinada Arriesgada */
  
  .slip-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,.04); padding-bottom:10px; }
  .slip-title { font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#fff; }
  .slip-quota { background:rgba(255,107,0,.15); color:#FF6B00; padding:4px 10px; border-radius:6px; font-weight:800; font-size:14px; border:1px solid rgba(255,107,0,.3); }
  
  .item-match { font-size:12px; font-weight:700; color:#8A97B5; margin-top:8px; text-transform:uppercase; letter-spacing:0.5px; }
  .item-bet { font-size:15px; color:#fff; font-weight:800; padding-left:16px; margin-bottom:8px; position:relative; }
  .item-bet::before { content:'🎯'; position:absolute; left:0; top:2px; font-size:12px; }
  
  .slip-desc { font-size:11px; color:#8A97B5; line-height:1.5; margin-top:12px; padding-top:10px; border-top:1px dashed rgba(255,255,255,.08); }

  /* -------------------------------------
     DASHBOARD Y ESTADÍSTICAS
     ------------------------------------- */
  .dash-container { display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; margin-bottom:20px; }
  .dash-card { background:#131F30; border:1px solid rgba(255,255,255,.06); border-radius:10px; padding:15px; text-align:center; }
  .dash-val { font-size:24px; font-weight:800; color:#fff; margin-bottom:4px; }
  .dash-lbl { font-size:10px; font-weight:700; color:#8A97B5; text-transform:uppercase; letter-spacing:0.5px; }
  
  /* -------------------------------------
     HISTORIAL MINIMALISTA
     ------------------------------------- */
  .st-expander { background:#0E1A2C !important; border:1px solid rgba(255,255,255,.06) !important; border-radius:10px !important; margin-bottom:10px !important; }
  .hist-row { display:flex; justify-content:space-between; align-items:center; background:#131F30; padding:12px; border-radius:8px; margin-bottom:8px; border-left:3px solid #4A5568; }
  .hist-meta { font-size:12px; color:#fff; font-weight:800; margin-bottom:2px; }
  .hist-bet-txt { font-size:11px; color:#8A97B5; }
  .badge-status { font-size:10px; font-weight:800; text-transform:uppercase; padding:3px 8px; border-radius:4px; letter-spacing:0.5px; }
  
  /* Mini botones manuales en historial */
  .mini-btn-group { display:flex; gap:4px; margin-top:8px; justify-content:flex-end; }
  .mini-btn { padding:4px 8px; font-size:10px; font-weight:700; border-radius:4px; border:1px solid rgba(255,255,255,.1); background:#0E1A2C; color:#8A97B5; cursor:pointer; }
  .mini-btn:hover { background:rgba(255,255,255,.05); }
</style>

<div class="hdr">
  <div class="logo">BET<span class="logo-bolt">⚡</span>COMBINADAS</div>
  <div class="badge-betano">🎯 MUNDIAL & BETANO</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 2. CONEXIONES (Supabase y APIs)
# ═══════════════════════════════════════════════════════════════
api_gemini = st.secrets.get("GEMINI_API", "") or st.session_state.get("_gem", "")
api_odds = st.secrets.get("ODDS_API", "") or st.session_state.get("_odd", "")
supa_url = st.secrets.get("SUPABASE_URL", "") or st.session_state.get("_supa_url", "")
supa_key = st.secrets.get("SUPABASE_KEY", "") or st.session_state.get("_supa_key", "")

if not (api_gemini and api_odds and supa_url and supa_key):
    st.warning("⚠️ Configura las credenciales en Streamlit Secrets para iniciar.")
    st.stop()

supabase: Client = create_client(supa_url, supa_key)

# ═══════════════════════════════════════════════════════════════
# 3. VERIFICADOR AUTÓNOMO Y BD
# ═══════════════════════════════════════════════════════════════
def auto_verificar_jornada():
    """Motor que lee marcadores finales y evalúa tickets pendientes."""
    try:
        pendientes = supabase.table("historial").select("*").or_(
            "res_estrella.eq.pendiente,res_mas_seguro.eq.pendiente,res_segura.eq.pendiente,res_moderada.eq.pendiente,res_arriesgada.eq.pendiente"
        ).execute().data
        
        if not pendientes: return
            
        # Obtener scores recientes
        url_scores = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/scores/?apiKey={api_odds}&daysFrom=3"
        r = requests.get(url_scores, timeout=10)
        if r.status_code != 200: return
        
        marcadores = r.json()
        partidos_terminados = {}
        
        # Mapear partidos terminados
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
            data_analisis = json.loads(ticket["analisis_json"])
            updates = {}
            
            columnas = [
                ('res_estrella', data_analisis.get('pick_estrella', {})),
                ('res_mas_seguro', data_analisis.get('pick_mas_seguro', {})),
                ('res_segura', data_analisis.get('estrategias', [{},{},{}])[0]),
                ('res_moderada', data_analisis.get('estrategias', [{},{},{}])[1]),
                ('res_arriesgada', data_analisis.get('estrategias', [{},{},{}])[2])
            ]
            
            for col, obj_apuesta in columnas:
                if ticket[col] != "pendiente" or not obj_apuesta: continue
                
                apuesta_txt = obj_apuesta.get("seleccion", "") or " | ".join(obj_apuesta.get("picks", []))
                partidos_del_ticket = [p for p in partidos_terminados.keys() if p in ticket["partidos"] or p in apuesta_txt]
                
                # Si hay partidos del ticket que ya terminaron, evaluamos
                if partidos_del_ticket:
                    marcas_str = "\n".join([partidos_terminados[p] for p in partidos_del_ticket])
                    prompt = f"""
                    Evalúa si esta apuesta se GANÓ o PERDIÓ según los marcadores finales.
                    MARCADORES REALES:
                    {marcas_str}
                    
                    APUESTA REALIZADA:
                    {apuesta_txt}
                    
                    Si todos los picks de la apuesta se cumplieron, responde solo "acertado".
                    Si al menos un pick falló o los resultados no alcanzan, responde solo "fallido".
                    Si faltan resultados para saberlo con certeza, responde solo "pendiente".
                    """
                    try:
                        res = client.models.generate_content(
                            model="gemini-3.1-flash-lite", 
                            contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.0)
                        ).text.strip().lower()
                        
                        if "acertado" in res: updates[col] = "acertado"
                        elif "fallido" in res: updates[col] = "fallido"
                    except: pass
            
            if updates:
                supabase.table("historial").update(updates).eq("id", ticket["id"]).execute()
    except Exception as e:
        pass

def guardar_ticket_db(liga, partidos_str, analisis_json):
    fecha = datetime.now(TZ_CHILE).strftime("%Y-%m-%d %H:%M")
    data = { "fecha_gen": fecha, "liga": liga, "partidos": partidos_str, "analisis_json": json.dumps(analisis_json, ensure_ascii=False) }
    try:
        supabase.table("historial").insert(data).execute()
        return True
    except: return False

def cargar_historial_db():
    try: return supabase.table("historial").select("*").order("id", desc=True).limit(30).execute().data
    except: return []

def actualizar_resultado_manual(ticket_id, campo, valor):
    supabase.table("historial").update({campo: valor}).eq("id", ticket_id).execute()

def eliminar_ticket_db(ticket_id):
    supabase.table("historial").delete().eq("id", ticket_id).execute()

# ═══════════════════════════════════════════════════════════════
# 4. INTELIGENCIA QUANT (Reglas Estrictas)
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_partidos_mundial(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h,totals,spreads"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e: return {"error": str(e)}

@st.cache_data(ttl=86400, show_spinner=False)
def ejecutar_algoritmo_quant(api_key, partidos_seleccionados):
    prompt = f"""
Eres un Analista Experto en Apuestas Deportivas. Tu único objetivo es GANAR DINERO construyendo boletos con la máxima probabilidad de acierto para el Mundial.

REGLA DE ORO 1 (FILOSOFÍA):
Busca opciones de altísima probabilidad con cuotas bajas (@1.20 a @1.40). El éxito es sumar aciertos, no buscar cuotas locas.

REGLA DE ORO 2 (ANTI-CORRELACIÓN - ¡ESTRICTO!):
NUNCA, bajo NINGUNA circunstancia, mezcles "Ganador Directo" y "Hándicap" del MISMO partido en una combinada. Betano prohíbe esto. O usas ganador, o usas hándicap, pero jamás ambos para un mismo evento en el mismo ticket.

MERCADOS PERMITIDOS: Ganador (1X2), Doble Oportunidad, Goles (Over/Under), Hándicap (respetando Regla 2).

ESTRUCTURA DE RETORNO OBLIGATORIA (Usar Betano o Promedio):
- SEGURA: 1 a 2 picks. Cuotas individuales muy bajas.
- MODERADA: 3 a 4 picks. Cuota total final entre @1.50 y @3.50.
- ARRIESGADA: 3 a 5 picks. Cuota total final entre @3.50 y @7.00.

PARTIDOS EN CRUDO:
{json.dumps(partidos_seleccionados, ensure_ascii=False, indent=2)}

Responde ÚNICAMENTE con este JSON estructurado (sin texto extra):
{{
  "game_script": "Análisis rápido de las oportunidades más seguras.",
  "pick_estrella": {{
    "partido": "Equipo A vs B",
    "categoria_permitida": "Total de Goles",
    "seleccion": "Over 1.5",
    "cuota_betano": 1.25,
    "razon_cuantitativa": "Razón de su altísima probabilidad."
  }},
  "pick_mas_seguro": {{
    "partido": "Equipo C vs D",
    "categoria_permitida": "Doble Oportunidad",
    "seleccion": "1X",
    "cuota_betano": 1.18,
    "razon_cuantitativa": "Justificación táctica."
  }},
  "estrategias": [
    {{
      "tipo": "segura",
      "cuota_total": 1.35,
      "descripcion": "Combinada para proteger capital.",
      "picks": ["Equipo A vs B: Over 1.5 (@1.25)", "Equipo C vs D: 1X (@1.08)"]
    }},
    {{
      "tipo": "moderada",
      "cuota_total": 2.20,
      "descripcion": "Multiplicador óptimo sin riesgo excesivo.",
      "picks": ["Pick 1 (@1.25)", "Pick 2 (@1.30)", "Pick 3 (@1.35)"]
    }},
    {{
      "tipo": "arriesgada",
      "cuota_total": 4.50,
      "descripcion": "Boleto extendido para maximizar ganancias.",
      "picks": ["Pick 1 (@1.30)", "Pick 2 (@1.40)", "Pick 3 (@1.35)", "Pick 4 (@1.25)"]
    }}
  ]
}}"""
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite", contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.1, response_mime_type="application/json")
        )
        raw_text = resp.text.strip()
        if raw_text.startswith("```json")
        return json.loads(raw_text)
    except Exception as e: return {"error": str(e)}

def fmt_fecha(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(TZ_CHILE).strftime('%d %b · %H:%M')
    except: return "Fecha N/D"

# ═══════════════════════════════════════════════════════════════
# 5. PANELES DE CONTROL (TABS)
# ═══════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["⚡ Armador de Boletos", "📊 Base & Stats"])

with tab1:
    st.markdown("<h4 style='color:#EEF4FF; font-weight:800; font-size:15px;'>🌍 Mercado: Mundial 2026</h4>", unsafe_allow_html=True)
    
    with st.spinner("Sincronizando cuotas globales..."):
        datos_api = obtener_partidos_mundial(api_odds)
    
    if isinstance(datos_api, dict) and "error" in datos_api: st.error("Error en la API de cuotas.")
    elif not datos_api: st.info("No hay partidos de la copa disponibles.")
    else:
        partidos_activos = []
        for p in datos_api[:10]:
            lbl = f"⚽ **{p['home_team']} vs {p['away_team']}** *(🕒 {fmt_fecha(p['commence_time'])})*"
            if st.checkbox(lbl, key=p['id']): partidos_activos.append(p)
        
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        
        if st.button("🚀 Construir Boletos (+EV)"):
            if not partidos_activos: st.warning("⚠️ Selecciona al menos un partido.")
            else:
                with st.spinner("🤖 Calculando combinaciones de alta probabilidad..."):
                    res = ejecutar_algoritmo_quant(api_gemini, partidos_activos)
                if "error" in res: st.error("Fallo en el motor de IA.")
                else:
                    st.session_state.ultimo_analisis = res
                    st.session_state.partidos_analizados = " | ".join([f"{p['home_team']} vs {p['away_team']}" for p in partidos_activos])
                    st.session_state.ticket_guardado = False

        if "ultimo_analisis" in st.session_state:
            data = st.session_state.ultimo_analisis
            
            st.markdown("<div style='height:20px;'></div><h4 style='color:#EEF4FF; font-weight:800; font-size:14px;'>🎟️ Boletos Generados</h4>", unsafe_allow_html=True)
            
            def render_ticket(clase_css, titulo, cuota, partido, seleccion, desc):
                st.markdown(f"""
                <div class="ticket-slip {clase_css}">
                  <div class="slip-header">
                    <span class="slip-title">{titulo}</span>
                    <span class="slip-quota">@{cuota}</span>
                  </div>
                  <div class="item-match">{partido}</div>
                  <div class="item-bet">{seleccion}</div>
                  <div class="slip-desc"><b>Veredicto:</b> {desc}</div>
                </div>
                """, unsafe_allow_html=True)

            pe = data.get('pick_estrella', {})
            render_ticket("slip-base", "⭐ Pick Base (Single)", pe.get('cuota_betano','-'), pe.get('partido',''), pe.get('seleccion',''), pe.get('razon_cuantitativa',''))
            
            ps = data.get('pick_mas_seguro', {})
            render_ticket("slip-anti", "🛡️ Pick Anti-Sorpresas", ps.get('cuota_betano','-'), ps.get('partido',''), ps.get('seleccion',''), ps.get('razon_cuantitativa',''))
            
            estrat_map = {"segura": ("slip-segura", "🟢 COMBINADA SEGURA"), "moderada": ("slip-moderada", "🟡 COMBINADA MODERADA"), "arriesgada": ("slip-arriesgada", "🔴 COMBINADA ARRIESGADA")}
            
            for e in data.get('estrategias', []):
                clase_css, tit = estrat_map.get(e.get('tipo', 'segura'), ("slip-segura", "Combinada"))
                picks_html = ""
                for pick in e.get('picks', []):
                    if ":" in pick: p_str, b_str = pick.split(":", 1)
                    else: p_str, b_str = "Partido", pick
                    picks_html += f'<div class="item-match">{p_str.strip()}</div><div class="item-bet">{b_str.strip()}</div>'
                
                st.markdown(f"""
                <div class="ticket-slip {clase_css}">
                  <div class="slip-header"><span class="slip-title">{tit}</span><span class="slip-quota">@{e.get('cuota_total', '-')}</span></div>
                  {picks_html}
                  <div class="slip-desc"><b>Estrategia:</b> {e.get('descripcion','')}</div>
                </div>
                """, unsafe_allow_html=True)

            if not st.session_state.get('ticket_guardado', False):
                st.markdown('<div class="btn-guardar">', unsafe_allow_html=True)
                if st.button("💾 Guardar Boletos en Supabase"):
                    if guardar_ticket_db("Mundial 2026", st.session_state.partidos_analizados, data):
                        st.session_state.ticket_guardado = True
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Guardado permanentemente en la Base de Datos.")

with tab2:
    with st.spinner("🤖 Evaluando resultados en vivo..."):
        auto_verificar_jornada()
        historial = cargar_historial_db()
    
    # --- DASHBOARD DE ESTADÍSTICAS ---
    acertados = 0
    fallidos = 0
    
    if historial:
        columnas_eval = ['res_estrella', 'res_mas_seguro', 'res_segura', 'res_moderada', 'res_arriesgada']
        for t in historial:
            for col in columnas_eval:
                if t.get(col) == 'acertado': acertados += 1
                elif t.get(col) == 'fallido': fallidos += 1
                
    total_res = acertados + fallidos
    hit_rate = int((acertados / total_res) * 100) if total_res > 0 else 0
    color_hr = "#00E676" if hit_rate >= 50 else "#FFB700" if hit_rate >= 30 else "#FF3B5C"

    st.markdown(f"""
    <div class="dash-container">
      <div class="dash-card">
        <div class="dash-val" style="color: {color_hr};">{hit_rate}%</div>
        <div class="dash-lbl">Hit Rate Global</div>
      </div>
      <div class="dash-card">
        <div class="dash-val" style="color:#00E676;">{acertados}</div>
        <div class="dash-lbl">Picks Acertados</div>
      </div>
      <div class="dash-card">
        <div class="dash-val" style="color:#FF3B5C;">{fallidos}</div>
        <div class="dash-lbl">Picks Fallados</div>
      </div>
    </div>
    <h4 style='color:#EEF4FF; font-weight:800; font-size:14px; margin-bottom:15px;'>📋 Historial de Operaciones</h4>
    """, unsafe_allow_html=True)
    
    # --- LISTA DE HISTORIAL ---
    if not historial:
        st.info("No hay registros. Guarda tus primeros boletos en la pestaña anterior.")
    else:
        for t in historial:
            data_t = json.loads(t['analisis_json'])
            with st.expander(f"🎫 {t['fecha_gen']} · {t['liga']}"):
                st.markdown(f"<div style='font-size:10px; color:#8A97B5; margin-bottom:12px;'><b>Eventos:</b> {t['partidos']}</div>", unsafe_allow_html=True)
                
                estrategias_lista = data_t.get('estrategias', [])
                
                items = [
                    ('res_estrella', '⭐ Pick Base', data_t.get('pick_estrella', {}).get('seleccion', 'N/D')),
                    ('res_mas_seguro', '🛡️ Pick Anti-Sorpresas', data_t.get('pick_mas_seguro', {}).get('seleccion', 'N/D')),
                    ('res_segura', '🟢 Combinada Segura', f"Cuota @{estrategias_lista[0].get('cuota_total', 'N/D')}" if len(estrategias_lista) > 0 else "N/D"),
                    ('res_moderada', '🟡 Combinada Moderada', f"Cuota @{estrategias_lista[1].get('cuota_total', 'N/D')}" if len(estrategias_lista) > 1 else "N/D"),
                    ('res_arriesgada', '🔴 Combinada Arriesgada', f"Cuota @{estrategias_lista[2].get('cuota_total', 'N/D')}" if len(estrategias_lista) > 2 else "N/D")
                ]
                
                for col_name, titulo, seleccion_txt in items:
                    estado = t.get(col_name, 'pendiente')
                    bg = "#00E676" if estado == "acertado" else "#FF3B5C" if estado == "fallido" else "#4A5568"
                    
                    st.markdown(f"""
                    <div class="hist-row" style="border-left-color: {bg};">
                      <div>
                        <div class="hist-meta">{titulo}</div>
                        <div class="hist-bet-txt">{seleccion_txt}</div>
                      </div>
                      <span class="badge-status" style="background: {bg}; color: #fff;">{estado}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3, c4 = st.columns([1,1,1,2])
                    if c1.button("✅", key=f"ok_{t['id']}_{col_name}", help="Acertado"): actualizar_resultado_manual(t['id'], col_name, 'acertado'); st.rerun()
                    if c2.button("❌", key=f"fa_{t['id']}_{col_name}", help="Fallido"): actualizar_resultado_manual(t['id'], col_name, 'fallido'); st.rerun()
                    if c3.button("⏳", key=f"pe_{t['id']}_{col_name}", help="Pendiente"): actualizar_resultado_manual(t['id'], col_name, 'pendiente'); st.rerun()
                
                st.markdown("<hr style='border-color:rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                if st.button("🗑️ Eliminar Registro", key=f"del_{t['id']}"):
                    eliminar_ticket_db(t['id']); st.rerun()


```
