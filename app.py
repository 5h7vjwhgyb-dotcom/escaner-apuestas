import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
import json
import os
from supabase import create_client, Client

try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-4))

# ═══════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN DE UI Y CSS
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="BET⚡COMBINADAS - Mundial", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background:#07101E !important; color:#EEF4FF !important; font-family:'Inter', sans-serif !important; }
  [data-testid="stHeader"] { background:transparent !important; }
  .block-container { padding-top:1rem !important; max-width:600px !important; }
  
  .hdr { display:flex; align-items:center; justify-content:space-between; padding:14px 20px; background:#0E1A2C; border:1px solid rgba(255,255,255,.06); border-radius:12px; margin-bottom:20px; }
  .logo { font-size:18px; font-weight:800; letter-spacing:-0.5px; }
  .logo-bolt { color:#00C2FF; }
  .badge-betano { background:rgba(255,107,0,.15); border:1px solid rgba(255,107,0,.3); padding:4px 10px; border-radius:20px; font-size:10px; font-weight:800; color:#FF6B00; text-transform:uppercase; }
  
  .stButton>button { background:linear-gradient(135deg,#00C2FF,#0091CC) !important; border:none !important; border-radius:8px !important; color:#fff !important; font-weight:800 !important; font-size:14px !important; width:100% !important; padding:0.7em !important; }
  .stButton>button:hover { opacity:0.9; }
  .btn-guardar>button { background:linear-gradient(135deg,#8B5CF6,#6D28D9) !important; margin-top:15px !important; }
  
  .st-expander { background:#131F30 !important; border:1px solid rgba(255,255,255,.06) !important; border-radius:10px !important; }
  hr { border-color:rgba(255,255,255,.06) !important; }
  [data-testid="stCheckbox"] { background:#131F30; padding:12px 15px; border-radius:8px; border:1px solid rgba(255,255,255,.06); margin-bottom:8px; }
  
  .pick { border-radius:8px; padding:16px; border:1px solid; margin-bottom:12px; background:#0E1A2C; }
  .pick-e { border-color:rgba(255,107,0,.35); }
  .pick-s { border-color:rgba(0,230,118,.25); }
  .plbl { font-size:9px; font-weight:800; letter-spacing:2px; text-transform:uppercase; margin-bottom:8px; }
  .plbl-e { color:#FF6B00; } .plbl-s { color:#00E676; }
  .pcat { font-size:10px; color:#8A97B5; font-weight:700; text-transform:uppercase; margin-bottom:8px; display:inline-block; border:1px solid rgba(255,255,255,.06); padding:3px 8px; border-radius:4px; }
  .qb { display:inline-flex; align-items:center; gap:4px; border-radius:6px; padding:5px 12px; font-size:13px; font-weight:800; margin-right:8px; margin-bottom:8px; }
  .qbet { background:rgba(255,107,0,.15); border:1px solid rgba(255,107,0,.3); color:#FF6B00; }
  .qmercado { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); color:#8A97B5; font-size:11px; }
  .estg { background:#18263A; border:1px solid rgba(255,255,255,.06); border-radius:8px; padding:14px; margin-bottom:10px; }
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
    st.warning("⚠️ Faltan claves. Configúralas en la nube de Streamlit o ingrésalas aquí.")
    with st.expander("⚙️ Ingresar Claves", expanded=True):
        st.text_input("Gemini API", type="password", key="_gem")
        st.text_input("Odds API", type="password", key="_odd")
        st.text_input("Supabase URL", type="password", key="_supa_url")
        st.text_input("Supabase Key", type="password", key="_supa_key")
        st.stop()

supabase: Client = create_client(supa_url, supa_key)

# ═══════════════════════════════════════════════════════════════
# 3. FUNCIONES DE SUPABASE
# ═══════════════════════════════════════════════════════════════
def guardar_ticket_db(liga, partidos_str, analisis_json):
    fecha = datetime.now(TZ_CHILE).strftime("%Y-%m-%d %H:%M")
    data = {
        "fecha_gen": fecha,
        "liga": liga,
        "partidos": partidos_str,
        "analisis_json": json.dumps(analisis_json, ensure_ascii=False)
    }
    try:
        supabase.table("historial").insert(data).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

def cargar_historial_db():
    try:
        response = supabase.table("historial").select("*").order("id", desc=True).limit(30).execute()
        return response.data
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        return []

def actualizar_resultado_db(ticket_id, campo, valor):
    try:
        supabase.table("historial").update({campo: valor}).eq("id", ticket_id).execute()
    except Exception as e:
        st.error(f"Error actualizando: {e}")

def eliminar_ticket_db(ticket_id):
    try:
        supabase.table("historial").delete().eq("id", ticket_id).execute()
    except Exception as e:
        st.error(f"Error eliminando: {e}")

# ═══════════════════════════════════════════════════════════════
# 4. FUNCIONES DEL CEREBRO QUANT (NUEVA FILOSOFÍA)
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_partidos_mundial(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h,totals,spreads"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=86400, show_spinner=False)
def ejecutar_algoritmo_quant(api_key, partidos_seleccionados):
    prompt = f"""
Eres un Analista Experto en Apuestas Deportivas y Combinadas (Parlays).
Tu ÚNICO objetivo es GANAR DINERO construyendo tickets con la mayor probabilidad de acierto posible para el Mundial de la FIFA, usando eventos muy probables.

FILOSOFÍA DE APUESTA (REGLA DE ORO):
Busca siempre la mayor cantidad de picks posibles usando CUOTAS INDIVIDUALES MUY BAJAS Y SEGURAS. Es preferible combinar 4 cuotas de @1.25 que son casi seguras, en lugar de usar cuotas altas peligrosas. No busques ineficiencias matemáticas raras, busca ACERTAR.

MERCADOS PERMITIDOS (¡NO USAR OTROS!):
1. Ganador Directo (1, X, 2)
2. Doble Oportunidad (1X, X2, 12)
3. Total de Goles (Over/Under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5)
4. Córners (Over/Under)
5. Tarjetas (Over/Under)
6. Hándicap Asiático o Europeo

ESTRUCTURA DE COMBINADAS OBLIGATORIA:
Debes armar EXACTAMENTE 3 estrategias (tickets) usando cuotas promedio o de Betano:
1. SEGURA: 1 a 2 picks como máximo. Cuotas individuales entre @1.20 y @1.40.
2. MODERADA: 3 a 4 picks combinados. La cuota TOTAL del ticket debe quedar entre @1.50 y @3.50. (Usa cuotas individuales bajas para llegar a este total).
3. ARRIESGADA: 3 a 5 picks combinados. La cuota TOTAL del ticket debe quedar entre @3.50 y @7.00. 

PARTIDOS DISPONIBLES (Datos en crudo):
{json.dumps(partidos_seleccionados, ensure_ascii=False, indent=2)}

Responde ÚNICAMENTE con este JSON exacto (sin texto markdown extra):
{{
  "game_script": "Resumen táctico de por qué estos partidos del Mundial son ideales para apostar a cuotas bajas.",
  "pick_estrella": {{
    "partido": "Local vs Visita",
    "categoria_permitida": "Ej: Total de Goles",
    "seleccion": "Ej: Over 1.5",
    "cuota_betano": 1.30,
    "cuota_promedio_mercado": 1.25,
    "razon_cuantitativa": "Por qué es el pick individual más seguro para incluir en cualquier combinada."
  }},
  "pick_mas_seguro": {{
    "partido": "Local vs Visita",
    "categoria_permitida": "Ej: Doble Oportunidad",
    "seleccion": "Ej: 1X",
    "cuota_betano": 1.22,
    "razon_cuantitativa": "Explicación de su altísima probabilidad de acierto."
  }},
  "estrategias": [
    {{
      "tipo": "segura",
      "cuota_total": 1.35,
      "descripcion": "Apuesta casi garantizada de 1 a 2 picks para proteger dinero.",
      "picks": ["Partido A: Selección (@1.20)", "Partido B: Selección (@1.12)"]
    }},
    {{
      "tipo": "moderada",
      "cuota_total": 2.45,
      "descripcion": "Multiplicador seguro usando 3 a 4 picks de alta probabilidad.",
      "picks": ["Pick 1 (@1.20)", "Pick 2 (@1.30)", "Pick 3 (@1.25)"]
    }},
    {{
      "tipo": "arriesgada",
      "cuota_total": 5.20,
      "descripcion": "Máximo beneficio combinando 3 a 5 picks manteniendo cuotas individuales sensatas.",
      "picks": ["Pick 1 (@1.40)", "Pick 2 (@1.35)", "Pick 3 (@1.45)", "Pick 4 (@1.30)"]
    }}
  ]
}}"""
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite", 
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.2, response_mime_type="application/json")
        )
        raw_text = resp.text.strip()
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3].strip()
        return json.loads(raw_text)
    except Exception as e:
        return {"error": str(e)}

def fmt_fecha(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(TZ_CHILE)
        return dt.strftime('%d %b · %H:%M')
    except: return "Fecha N/D"

# ═══════════════════════════════════════════════════════════════
# 5. INTERFAZ DE USUARIO (TABS)
# ═══════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["⚡ Armador de Combinadas", "📋 Base de Datos"])

with tab1:
    st.markdown("<h4 style='color:#EEF4FF; font-weight:800; font-size:15px;'>🌍 Partidos del Mundial</h4>", unsafe_allow_html=True)
    
    with st.spinner("Sincronizando cuotas globales..."):
        datos_api = obtener_partidos_mundial(api_odds)
    
    if isinstance(datos_api, dict) and "error" in datos_api:
        st.error("Error en la API de cuotas. Verifica tu clave.")
    elif not datos_api:
        st.info("No hay partidos del Mundial disponibles en este momento.")
    else:
        partidos_activos = []
        for p in datos_api[:10]:
            lbl = f"⚽ **{p['home_team']} vs {p['away_team']}** *(🕒 {fmt_fecha(p['commence_time'])})*"
            if st.checkbox(lbl, key=p['id']):
                partidos_activos.append(p)
        
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        
        if st.button("🚀 Armar Combinadas de Alta Probabilidad"):
            if not partidos_activos:
                st.warning("⚠️ Selecciona al menos un partido.")
            else:
                with st.spinner("🤖 Analizando opciones de alta probabilidad..."):
                    resultado = ejecutar_algoritmo_quant(api_gemini, partidos_activos)
                    
                if "error" in resultado:
                    st.error(f"Error de IA: {resultado['error']}")
                else:
                    st.session_state.ultimo_analisis = resultado
                    st.session_state.partidos_analizados = " | ".join([f"{p['home_team']} vs {p['away_team']}" for p in partidos_activos])
                    st.session_state.ticket_guardado = False

        # RENDERIZAR RESULTADO
        if "ultimo_analisis" in st.session_state:
            data = st.session_state.ultimo_analisis
            
            st.markdown("<div style='height:20px;'></div><h4 style='color:#EEF4FF; font-weight:800; font-size:15px;'>📖 Lectura del Mercado</h4>", unsafe_allow_html=True)
            st.markdown(f"<div style='background:#18263A; border-left:3px solid #00C2FF; padding:12px; border-radius:0 8px 8px 0; font-size:12px; color:#8A97B5; margin-bottom:15px;'>{data.get('game_script','')}</div>", unsafe_allow_html=True)
            
            pe = data.get('pick_estrella', {})
            st.markdown(f"""
            <div class="pick pick-e">
              <div class="plbl plbl-e">⭐ El Pick Base (Casi Seguro)</div>
              <span style="font-weight:800; font-size:14px; display:block; margin-bottom:4px;">{pe.get('partido','')}</span>
              <span class="pcat">📁 {pe.get('categoria_permitida','')}</span>
              <div style="margin-bottom:12px; font-size:15px;">Selección: <b style="color:#fff;">{pe.get('seleccion','')}</b></div>
              <div><span class="qb qbet">🔴 Betano @{pe.get('cuota_betano','')}</span></div>
              <div style="font-size:11px; color:#8A97B5; line-height:1.5; border-top:1px solid rgba(255,255,255,.06); padding-top:10px; margin-top:10px;">
                <b>🤖 Veredicto:</b> {pe.get('razon_cuantitativa','')}
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            ps = data.get('pick_mas_seguro', {})
            st.markdown(f"""
            <div class="pick pick-s">
              <div class="plbl plbl-s">🛡️ Pick Anti-Sorpresas</div>
              <span style="font-weight:800; font-size:14px; display:block; margin-bottom:4px;">{ps.get('partido','')}</span>
              <span class="pcat">📁 {ps.get('categoria_permitida','')}</span>
              <div style="margin-bottom:12px; font-size:15px;">Selección: <b style="color:#fff;">{ps.get('seleccion','')}</b></div>
              <div><span class="qb" style="background:rgba(0,230,118,.15); border:1px solid rgba(0,230,118,.4); color:#00E676;">🔴 Betano @{ps.get('cuota_betano','')}</span></div>
              <div style="font-size:11px; color:#8A97B5; line-height:1.5; border-top:1px solid rgba(255,255,255,.06); padding-top:10px; margin-top:10px;">
                <b>🤖 Veredicto:</b> {ps.get('razon_cuantitativa','')}
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<h4 style='color:#EEF4FF; font-weight:800; font-size:15px; margin-top:20px;'>🔗 Combinadas Sugeridas</h4>", unsafe_allow_html=True)
            for e in data.get('estrategias', []):
                color = "#00E676" if e['tipo'] == "segura" else "#FFB700" if e['tipo'] == "moderada" else "#FF3B5C"
                st.markdown(f"""
                <div class="estg">
                  <div style="font-weight:800; color:{color}; text-transform:uppercase; font-size:11px; margin-bottom:6px;">{e['tipo']} · Cuota Total: @{e['cuota_total']}</div>
                  <div style="font-size:12px; margin-bottom:8px;">{e['descripcion']}</div>
                  <div style="font-size:11px; color:#8A97B5; background:#0E1A2C; padding:8px; border-radius:6px;">{ '<br>➕ '.join(e.get('picks',[])) }</div>
                </div>
                """, unsafe_allow_html=True)

            if not st.session_state.get('ticket_guardado', False):
                st.markdown('<div class="btn-guardar">', unsafe_allow_html=True)
                if st.button("💾 Guardar Ticket en la Nube (Supabase)"):
                    exito, msg_error = guardar_ticket_db("Mundial 2026", st.session_state.partidos_analizados, data)
                    if exito:
                        st.session_state.ticket_guardado = True
                        st.rerun()
                    else:
                        st.error(f"❌ Error de Supabase: {msg_error}. Asegúrate de haber ejecutado el comando para deshabilitar RLS en Supabase.")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Ticket guardado para siempre. Revisa la pestaña Base de Datos.")

with tab2:
    st.markdown("<h4 style='color:#EEF4FF; font-weight:800; font-size:15px;'>📋 Base de Datos de Combinadas</h4>", unsafe_allow_html=True)
    historial = cargar_historial_db()
    
    if not historial:
        st.info("Aún no has guardado análisis. ¡Tus datos se sincronizarán con Supabase aquí!")
    else:
        for t in historial:
            data = json.loads(t['analisis_json'])
            with st.expander(f"🎫 {t['fecha_gen']} · {t['liga']}"):
                st.markdown(f"<div style='font-size:10px; color:#8A97B5; margin-bottom:10px;'>{t['partidos']}</div>", unsafe_allow_html=True)
                
                for key_res, label, pick_data in [
                    ('res_estrella', '⭐ Pick Base', data.get('pick_estrella',{})),
                    ('res_mas_seguro', '🛡️ Pick Anti-Sorpresas', data.get('pick_mas_seguro',{}))
                ]:
                    estado = t[key_res]
                    color = "#00E676" if estado == "acertado" else "#FF3B5C" if estado == "fallido" else "#8A97B5"
                    
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; background:#0E1A2C; padding:10px; border-radius:6px; margin-bottom:6px; border-left:3px solid {color};">
                      <div>
                        <div style="font-size:10px; font-weight:800;">{label}</div>
                        <div style="font-size:11px; color:#8A97B5;">{pick_data.get('seleccion','')}</div>
                      </div>
                      <span style="font-size:10px; font-weight:700; color:{color}; text-transform:uppercase;">{estado}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    if c1.button("✅", key=f"ac_{t['id']}_{key_res}"): actualizar_resultado_db(t['id'], key_res, 'acertado'); st.rerun()
                    if c2.button("❌", key=f"fa_{t['id']}_{key_res}"): actualizar_resultado_db(t['id'], key_res, 'fallido'); st.rerun()
                    if c3.button("⏳", key=f"pe_{t['id']}_{key_res}"): actualizar_resultado_db(t['id'], key_res, 'pendiente'); st.rerun()
                
                st.markdown("<hr>", unsafe_allow_html=True)
                if st.button("🗑️ Eliminar Registro", key=f"del_{t['id']}"):
                    eliminar_ticket_db(t['id']); st.rerun()
