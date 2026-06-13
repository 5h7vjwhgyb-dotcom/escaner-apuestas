import streamlit as st
import requests
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
import json
import sqlite3
import os

try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-4))

# ═══════════════════════════════════════════════
# TRADUCCIONES Y BANDERAS
# ═══════════════════════════════════════════════
TRADUCCIONES = {
    "South Korea":"Corea del Sur","Czech Republic":"República Checa","Czechia":"República Checa",
    "Bosnia and Herzegovina":"Bosnia y Herz.","Bosnia & Herzegovina":"Bosnia y Herz.",
    "Canada":"Canadá","USA":"Estados Unidos","United States":"Estados Unidos",
    "Switzerland":"Suiza","Turkey":"Turquía","Turkiye":"Turquía","Germany":"Alemania",
    "Ivory Coast":"Costa de Marfil","Brazil":"Brasil","Morocco":"Marruecos","Haiti":"Haití",
    "Scotland":"Escocia","Spain":"España","Cabo Verde":"Cabo Verde","Saudi Arabia":"Arabia Saudita",
    "Croatia":"Croacia","New Zealand":"Nueva Zelanda","France":"Francia","Japan":"Japón",
    "DR Congo":"RD Congo","Congo DR":"RD Congo","Uzbekistan":"Uzbekistán","England":"Inglaterra",
    "Netherlands":"Países Bajos","Belgium":"Bélgica","Cameroon":"Camerún","Peru":"Perú",
    "Iran":"Irán","Denmark":"Dinamarca","Poland":"Polonia","Sweden":"Suecia","Norway":"Noruega",
    "Ukraine":"Ucrania","Wales":"Gales","Algeria":"Argelia","Egypt":"Egipto","Tunisia":"Túnez",
    "Panama":"Panamá","Jamaica":"Jamaica","Iraq":"Irak","Romania":"Rumania","Hungary":"Hungría",
    "Slovakia":"Eslovaquia","Slovenia":"Eslovenia","Ireland":"Irlanda","New Caledonia":"N. Caledonia"
}

BANDERAS = {
    "Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷","Korea Republic":"🇰🇷",
    "Czechia":"🇨🇿","Czech Republic":"🇨🇿","USA":"🇺🇸","United States":"🇺🇸","Paraguay":"🇵🇾",
    "Canada":"🇨🇦","Bosnia and Herzegovina":"🇧🇦","Bosnia & Herzegovina":"🇧🇦","Qatar":"🇶🇦",
    "Switzerland":"🇨🇭","Australia":"🇦🇺","Turkey":"🇹🇷","Turkiye":"🇹🇷","Germany":"🇩🇪",
    "Curacao":"🇨🇼","Ivory Coast":"🇨🇮","Ecuador":"🇪🇨","Brazil":"🇧🇷","Morocco":"🇲🇦",
    "Haiti":"🇭🇹","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Spain":"🇪🇸","Cabo Verde":"🇨🇻","Saudi Arabia":"🇸🇦",
    "Argentina":"🇦🇷","Croatia":"🇭🇷","New Zealand":"🇳🇿","Senegal":"🇸🇳","France":"🇫🇷",
    "Japan":"🇯🇵","Colombia":"🇨🇴","Portugal":"🇵🇹","DR Congo":"🇨🇩","Congo DR":"🇨🇩",
    "Uzbekistan":"🇺🇿","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Netherlands":"🇳🇱","Belgium":"🇧🇪","Nigeria":"🇳🇬",
    "Cameroon":"🇨🇲","Ghana":"🇬🇭","Uruguay":"🇺🇾","Chile":"🇨🇱","Peru":"🇵🇪","Venezuela":"🇻🇪",
    "Iran":"🇮🇷","Serbia":"🇷🇸","Denmark":"🇩🇰","Poland":"🇵🇱","Sweden":"🇸🇪","Norway":"🇳🇴",
    "Ukraine":"🇺🇦","Wales":"🏴󠁧󠁢󠁷󠁬󠁳󠁿","Algeria":"🇩🇿","Egypt":"🇪🇬","Tunisia":"🇹🇳",
    "Costa Rica":"🇨🇷","Panama":"🇵🇦","Honduras":"🇭🇳","Jamaica":"🇯🇲","UAE":"🇦🇪","Iraq":"🇮🇶",
    "China":"🇨🇳","Indonesia":"🇮🇩","Greece":"🇬🇷","Romania":"🇷🇴","Hungary":"🇭🇺",
    "Slovakia":"🇸🇰","Slovenia":"🇸🇮","Austria":"🇦🇹","Finland":"🇫🇮","Ireland":"🇮🇪","New Caledonia":"🇳🇨",
}

LIGAS = {
    "🌍 Mundial 2026 (ACTIVO)":      "soccer_fifa_world_cup",
    "🇺🇸 MLS (ACTIVO)":               "soccer_usa_mls",
    "🇧🇷 Copa Libertadores (ACTIVO)": "soccer_conmebol_copa_libertadores",
    "🇬🇧 Premier League":              "soccer_epl",
    "🇪🇸 La Liga":                     "soccer_spain_la_liga",
    "🇩🇪 Bundesliga":                  "soccer_germany_bundesliga",
    "🇮🇹 Serie A":                     "soccer_italy_serie_a",
    "🇫🇷 Ligue 1":                     "soccer_france_ligue_one",
    "🏆 Champions League":             "soccer_uefa_champs_league",
}

# ═══════════════════════════════════════════════
# SISTEMA DE HISTORIAL — SQLite
# ═══════════════════════════════════════════════
DB_PATH = "bet_historial.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS historial (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_gen       TEXT NOT NULL,
        liga            TEXT NOT NULL,
        partidos        TEXT NOT NULL,
        game_script     TEXT DEFAULT '',
        pick_estrella   TEXT DEFAULT '{}',
        pick_mas_seguro TEXT DEFAULT '{}',
        est_segura      TEXT DEFAULT '{}',
        est_moderada    TEXT DEFAULT '{}',
        est_arriesgada  TEXT DEFAULT '{}',
        res_estrella    TEXT DEFAULT 'pendiente',
        res_mas_seguro  TEXT DEFAULT 'pendiente',
        res_segura      TEXT DEFAULT 'pendiente',
        res_moderada    TEXT DEFAULT 'pendiente',
        res_arriesgada  TEXT DEFAULT 'pendiente'
    )''')
    conn.commit()
    conn.close()

def guardar_ticket_db(liga, partidos_str, game_script, pick_estrella, pick_mas_seguro, estrategias):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fecha = datetime.now(TZ_CHILE).strftime("%Y-%m-%d %H:%M")
    c.execute('''INSERT INTO historial
        (fecha_gen,liga,partidos,game_script,pick_estrella,pick_mas_seguro,est_segura,est_moderada,est_arriesgada)
        VALUES (?,?,?,?,?,?,?,?,?)''',
        (fecha, liga, partidos_str, game_script,
         json.dumps(pick_estrella, ensure_ascii=False),
         json.dumps(pick_mas_seguro, ensure_ascii=False),
         json.dumps(estrategias[0] if len(estrategias)>0 else {}, ensure_ascii=False),
         json.dumps(estrategias[1] if len(estrategias)>1 else {}, ensure_ascii=False),
         json.dumps(estrategias[2] if len(estrategias)>2 else {}, ensure_ascii=False)))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid

def actualizar_resultado_db(ticket_id, campo, valor):
    validos = {'res_estrella','res_mas_seguro','res_segura','res_moderada','res_arriesgada'}
    if campo not in validos: return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f'UPDATE historial SET {campo}=? WHERE id=?', (valor, ticket_id))
    conn.commit()
    conn.close()

def eliminar_ticket_db(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM historial WHERE id=?', (ticket_id,))
    conn.commit()
    conn.close()

def cargar_historial_db(limit=40):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM historial ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def calcular_estadisticas_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM historial')
    total = c.fetchone()[0]
    if total == 0:
        conn.close()
        return None
    stats = {'total': total}
    campos = {
        'estrella':'res_estrella','mas_seguro':'res_mas_seguro',
        'segura':'res_segura','moderada':'res_moderada','arriesgada':'res_arriesgada'
    }
    for nombre, campo in campos.items():
        c.execute(f'SELECT COUNT(*) FROM historial WHERE {campo}!="pendiente"')
        con_res = c.fetchone()[0]
        c.execute(f'SELECT COUNT(*) FROM historial WHERE {campo}="acertado"')
        acertados = c.fetchone()[0]
        stats[nombre] = {
            'con_resultado': con_res, 'acertados': acertados,
            'fallidos': con_res - acertados,
            'porcentaje': round(acertados/con_res*100) if con_res>0 else None
        }
    total_con = sum(stats[k]['con_resultado'] for k in campos)
    total_ac  = sum(stats[k]['acertados']     for k in campos)
    stats['global'] = {
        'con_resultado': total_con, 'acertados': total_ac,
        'porcentaje': round(total_ac/total_con*100) if total_con>0 else None
    }
    conn.close()
    return stats

init_db()

# ═══════════════════════════════════════════════
# API CACHEADAS
# ═══════════════════════════════════════════════
@st.cache_data(ttl=21600, persist="disk", show_spinner=False)
def obtener_partidos_api(liga, api_key):
    url = (f"https://api.the-odds-api.com/v4/sports/{liga}/odds/"
           f"?apiKey={api_key}&regions=eu&markets=h2h,totals,spreads")
    try:
        r = requests.get(url, timeout=10)
        return r.json(), r.headers.get("x-requests-remaining","?")
    except Exception as e:
        return {"message": str(e)}, "?"

@st.cache_data(ttl=43200, persist="disk", show_spinner=False)
def obtener_estadisticas_futbol(local, visita, api_key):
    if not api_key: return {"error":"Falta Football API Key"}
    headers = {'X-Auth-Token': api_key}
    stats = {"estado_forma_local":"Desconocido","estado_forma_visita":"Desconocido",
             "posicion_local":"N/A","posicion_visita":"N/A"}
    try:
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fut  = (datetime.now(timezone.utc)+timedelta(days=10)).strftime("%Y-%m-%d")
        r = requests.get(f"https://api.football-data.org/v4/matches?dateFrom={hoy}&dateTo={fut}",
                         headers=headers, timeout=10)
        if r.status_code != 200: return {"error":f"Error API: {r.status_code}"}
        for m in r.json().get("matches",[]):
            ha = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            aa = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            if (local.lower() in ha.lower() or ha.lower() in local.lower()) and \
               (visita.lower() in aa.lower() or aa.lower() in visita.lower()):
                stats["estado_forma_local"]  = m.get("homeTeam",{}).get("form","N/A")
                stats["estado_forma_visita"] = m.get("awayTeam",{}).get("form","N/A")
                code = m['competition']['code']
                rs = requests.get(f"https://api.football-data.org/v4/competitions/{code}/standings",
                                  headers=headers, timeout=10)
                if rs.status_code == 200:
                    for tbl in rs.json().get("standings",[]):
                        if tbl["type"]=="TOTAL":
                            for row in tbl["table"]:
                                if row["team"]["id"]==m["homeTeam"]["id"]:
                                    stats["posicion_local"] = f"{row['position']}° ({row['points']}pts GF:{row['goalsFor']} GC:{row['goalsAgainst']})"
                                elif row["team"]["id"]==m["awayTeam"]["id"]:
                                    stats["posicion_visita"] = f"{row['position']}° ({row['points']}pts GF:{row['goalsFor']} GC:{row['goalsAgainst']})"
                break
        return stats
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=86400, persist="disk", show_spinner=False)
def obtener_analisis_ia(api_key, prompt, id_combinacion):
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.2,
                                           response_mime_type="application/json"))
    return json.loads(resp.text)

# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def flag(team): return BANDERAS.get(team,"🏳️")

def extraer_odds(partido):
    home = partido.get("home_team",""); away = partido.get("away_team","")
    h2h = {"home":None,"draw":None,"away":None}
    t_over, t_under, otros = {}, {}, {}
    for bk in partido.get("bookmakers",[]):
        for mkt in bk.get("markets",[]):
            k = mkt["key"]
            if k=="h2h":
                for o in mkt["outcomes"]:
                    p=o["price"]
                    if o["name"]==home:
                        if h2h["home"] is None or p>h2h["home"]: h2h["home"]=round(p,2)
                    elif o["name"]==away:
                        if h2h["away"] is None or p>h2h["away"]: h2h["away"]=round(p,2)
                    elif o["name"]=="Draw":
                        if h2h["draw"] is None or p>h2h["draw"]: h2h["draw"]=round(p,2)
            elif k=="totals":
                for o in mkt["outcomes"]:
                    pt=o.get("point",2.5); p=o["price"]
                    if o["name"]=="Over":
                        if pt not in t_over or p>t_over[pt]: t_over[pt]=round(p,2)
                    else:
                        if pt not in t_under or p>t_under[pt]: t_under[pt]=round(p,2)
            else:
                if k not in otros: otros[k]={}
                for o in mkt["outcomes"]:
                    lbl=f"{o['name']} {o.get('point','')} {o.get('description','')}".strip()
                    pr=round(o["price"],2)
                    if lbl not in otros[k] or pr>otros[k][lbl]: otros[k][lbl]=pr
    return h2h, t_over, t_under, otros

def calcular_probs(h2h):
    if not all(v is not None for v in h2h.values()): return {"home":40,"draw":30,"away":30}
    ph,pd,pa = 1/h2h["home"],1/h2h["draw"],1/h2h["away"]; total=ph+pd+pa
    hp=round(ph/total*100); dp=round(pd/total*100)
    return {"home":hp,"draw":dp,"away":100-hp-dp}

def mejor_apuesta(h2h,probs,t_over,t_under,home_es,away_es):
    cands=[]
    for pt in sorted(t_over.keys()):
        if pt in t_under:
            tot=(1/t_over[pt])+(1/t_under[pt])
            cands.append({"label":f"Más de {pt} Goles","odds":t_over[pt],"prob":round((1/t_over[pt])/tot*100)})
            cands.append({"label":f"Menos de {pt} Goles","odds":t_under[pt],"prob":round((1/t_under[pt])/tot*100)})
    if h2h["home"]: cands.append({"label":f"Gana {home_es}","odds":h2h["home"],"prob":probs["home"]})
    if h2h["draw"]: cands.append({"label":"Empate","odds":h2h["draw"],"prob":probs["draw"]})
    if h2h["away"]: cands.append({"label":f"Gana {away_es}","odds":h2h["away"],"prob":probs["away"]})
    return max(cands,key=lambda x:x["prob"]) if cands else None

def fmt_fecha(iso, simple=False):
    try:
        dt=datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(TZ_CHILE)
        if simple: return dt.strftime('%Y-%m-%d')
        dias=["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"]
        meses=["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt.isoweekday()%7]} {dt.day} {meses[dt.month]} · {dt.strftime('%H:%M')} (Chile)"
    except: return "Fecha N/D"

def render_simplified_card(partido, idx=1):
    home_en=partido.get("home_team","Local"); away_en=partido.get("away_team","Visita")
    home_es=TRADUCCIONES.get(home_en,home_en); away_es=TRADUCCIONES.get(away_en,away_en)
    h2h,t_over,t_under,_=extraer_odds(partido)
    probs=calcular_probs(h2h); best=mejor_apuesta(h2h,probs,t_over,t_under,home_es,away_es)
    hp,dp,ap=probs["home"],probs["draw"],probs["away"]
    odd_h=f"@{h2h['home']}" if h2h.get('home') else "N/A"
    odd_d=f"@{h2h['draw']}" if h2h.get('draw') else "N/A"
    odd_a=f"@{h2h['away']}" if h2h.get('away') else "N/A"
    best_html=""
    if best:
        best_html=f'<div style="background:#00e67615;color:#00e676;border:1px solid #00e67640;padding:6px;border-radius:8px;font-size:12px;font-weight:700;text-align:center;margin-top:12px;">💡 Valor Matemático: {best["label"]} ({best["odds"]})</div>'
    return f"""<div style="background:#161c2b;border-radius:12px;padding:14px;border:1px solid #2a3349;margin-bottom:14px;">
<div style="display:flex;justify-content:space-between;margin-bottom:12px;">
<span style="color:#8b949e;font-size:12px;font-weight:600;">📅 {fmt_fecha(partido.get('commence_time',''))}</span>
<span style="background:#2d3748;color:#e1e1e1;font-size:10px;padding:3px 8px;border-radius:20px;font-weight:800;">M {idx}</span></div>
<div style="display:flex;align-items:center;margin-bottom:14px;">
<div style="flex:1;text-align:center;"><div style="font-size:36px;line-height:1.1;margin-bottom:4px;">{flag(home_en)}</div>
<div style="color:#e1e1e1;font-weight:700;font-size:13px;">{home_es}</div>
<div style="color:#00e676;font-size:12px;font-weight:800;margin-top:2px;">{odd_h}</div></div>
<div style="flex:1;text-align:center;"><div style="color:#6b7280;font-size:13px;font-weight:900;letter-spacing:1px;margin-bottom:2px;">VS</div>
<div style="color:#8b949e;font-size:10px;font-weight:600;">EMP</div>
<div style="color:#e1e1e1;font-size:12px;font-weight:700;">{odd_d}</div></div>
<div style="flex:1;text-align:center;"><div style="font-size:36px;line-height:1.1;margin-bottom:4px;">{flag(away_en)}</div>
<div style="color:#e1e1e1;font-weight:700;font-size:13px;">{away_es}</div>
<div style="color:#00e676;font-size:12px;font-weight:800;margin-top:2px;">{odd_a}</div></div></div>
<div style="display:flex;border-radius:8px;overflow:hidden;height:22px;">
<div style="background:#22c55e;width:{hp}%;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:800;min-width:24px;">{hp}%</div>
<div style="background:#4b5563;width:{dp}%;display:flex;align-items:center;justify-content:center;color:#e1e1e1;font-size:10px;font-weight:600;min-width:24px;">{dp}%</div>
<div style="background:#ef4444;width:{ap}%;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:800;min-width:24px;">{ap}%</div></div>
{best_html}</div>"""

# ═══════════════════════════════════════════════
# RENDER HISTORIAL — TICKET CARD
# ═══════════════════════════════════════════════
def render_ticket_historial(t):
    try:
        pdatos = json.loads(t.get('partidos','[]'))
        equipos = " · ".join([f"{p.get('local','?')} vs {p.get('visita','?')}" for p in pdatos[:2]])
        if len(pdatos)>2: equipos += f" +{len(pdatos)-2}"
    except: equipos = "Partidos"

    campos_res = ['res_estrella','res_mas_seguro','res_segura','res_moderada','res_arriesgada']
    resultados = [t.get(r,'pendiente') for r in campos_res]
    n_ac = resultados.count('acertado')
    n_fa = resultados.count('fallido')
    n_cr = n_ac + n_fa
    pct  = round(n_ac/n_cr*100) if n_cr>0 else None
    pct_color = '#22c55e' if (pct or 0)>=60 else '#f59e0b' if (pct or 0)>=40 else '#ef4444'
    pct_badge = (f'<span style="background:{pct_color}25;color:{pct_color};font-size:11px;font-weight:800;padding:3px 10px;border-radius:10px;">🎯 {pct}% aciertos</span>'
                 if pct is not None else
                 '<span style="color:#4b5563;font-size:11px;">⏳ Sin resultados aún</span>')

    with st.expander(f"🎫 Ticket #{t['id']}  ·  {t['fecha_gen']}"):
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div>
            <div style="color:#8b949e;font-size:10px;font-weight:700;">{t['liga']}</div>
            <div style="color:#cbd5e1;font-size:12px;margin-top:2px;">{equipos}</div>
          </div>
          <div>{pct_badge}</div>
        </div>
        """, unsafe_allow_html=True)

        # Barra de progreso del ticket
        if n_cr > 0:
            bar_pct = round(n_ac/5*100)
            st.markdown(f"""
            <div style="background:#0a0f1e;border-radius:8px;padding:8px 12px;margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                <span style="color:#8b949e;font-size:10px;font-weight:700;">MARCADOR DEL TICKET</span>
                <span style="color:#e1e1e1;font-size:10px;font-weight:800;">{n_ac} ✅ &nbsp; {n_fa} ❌ &nbsp; {5-n_cr} ⏳</span>
              </div>
              <div style="background:#1e293b;border-radius:4px;height:7px;overflow:hidden;">
                <div style="width:{bar_pct}%;background:linear-gradient(90deg,#22c55e,#10b981);height:100%;border-radius:4px;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Cada pick con sus botones
        items = [
            ('res_estrella',   'pick_estrella',   '⭐', 'Pick Estrella',         True),
            ('res_mas_seguro', 'pick_mas_seguro', '🛡️', 'Pick Más Seguro',       True),
            ('res_segura',     'est_segura',      '🛡️', 'Estrategia Segura',     False),
            ('res_moderada',   'est_moderada',    '⚖️', 'Estrategia Moderada',   False),
            ('res_arriesgada', 'est_arriesgada',  '🔥', 'Estrategia Arriesgada', False),
        ]
        COLOR = {'acertado':'#22c55e','fallido':'#ef4444','pendiente':'#4b5563'}
        BADGE = {'acertado':'✅ Acertado','fallido':'❌ Fallido','pendiente':'⏳ Pendiente'}

        for res_campo, data_campo, emoji, label, es_pick in items:
            resultado = t.get(res_campo,'pendiente')
            try:
                raw = json.loads(t.get(data_campo,'{}'))
                if es_pick:
                    sel   = raw.get('seleccion','N/A')
                    cuota = raw.get('cuota','N/A')
                    info  = f"{sel} · @{cuota}"
                else:
                    picks  = raw.get('picks',[])
                    ctotal = raw.get('cuota_total','N/A')
                    sels   = " + ".join([p.get('seleccion','') for p in picks[:2]])
                    if len(picks)>2: sels += f" +{len(picks)-2} más"
                    info   = f"@{ctotal}  —  {sels}"
            except: info = "N/A"

            col = COLOR[resultado]
            st.markdown(f"""
            <div style="background:#0a0f1e;border-radius:8px;padding:9px 12px;margin-bottom:4px;border-left:3px solid {col};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="flex:1;padding-right:8px;">
                  <div style="color:#6b7280;font-size:10px;font-weight:700;">{emoji} {label}</div>
                  <div style="color:#e1e1e1;font-size:11px;font-weight:600;margin-top:2px;">{info[:70]}{'…' if len(info)>70 else ''}</div>
                </div>
                <span style="background:{col}20;color:{col};font-size:9px;font-weight:800;padding:3px 7px;border-radius:6px;white-space:nowrap;">{BADGE[resultado]}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            c1,c2,c3 = st.columns(3)
            with c1:
                if st.button("✅ Acertó", key=f"ac_{t['id']}_{res_campo}",
                             use_container_width=True, disabled=(resultado=='acertado')):
                    actualizar_resultado_db(t['id'], res_campo, 'acertado'); st.rerun()
            with c2:
                if st.button("❌ Falló", key=f"fa_{t['id']}_{res_campo}",
                             use_container_width=True, disabled=(resultado=='fallido')):
                    actualizar_resultado_db(t['id'], res_campo, 'fallido'); st.rerun()
            with c3:
                if st.button("⏳ Reset", key=f"pe_{t['id']}_{res_campo}",
                             use_container_width=True, disabled=(resultado=='pendiente')):
                    actualizar_resultado_db(t['id'], res_campo, 'pendiente'); st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button(f"🗑️ Eliminar Ticket #{t['id']}", key=f"del_{t['id']}", use_container_width=True):
            eliminar_ticket_db(t['id']); st.rerun()

# ═══════════════════════════════════════════════
# RENDER ESTADÍSTICAS — DASHBOARD
# ═══════════════════════════════════════════════
def render_stats_dashboard(stats):
    if not stats or stats['total']==0:
        st.markdown("""
        <div style="background:#161c2b;border:1px dashed #2d3748;border-radius:12px;padding:20px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">📭</div>
          <div style="color:#8b949e;font-size:13px;">Aún no hay tickets registrados.</div>
          <div style="color:#4b5563;font-size:12px;margin-top:4px;">Genera un análisis y guárdalo para comenzar tu historial.</div>
        </div>""", unsafe_allow_html=True)
        return

    g = stats['global']
    g_pct = g['porcentaje']
    g_col = '#22c55e' if (g_pct or 0)>=60 else '#f59e0b' if (g_pct or 0)>=40 else '#ef4444'

    # Métricas globales
    c1,c2,c3 = st.columns(3)
    for col, titulo, valor, color in [
        (c1, "TICKETS", str(stats['total']), '#e1e1e1'),
        (c2, "✅ ACERTADOS", str(g['acertados']), '#22c55e'),
        (c3, "% GLOBAL", f"{g_pct}%" if g_pct is not None else "N/A", g_col),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:#161c2b;border-radius:10px;padding:12px;text-align:center;border:1px solid #2d3748;">
              <div style="color:#8b949e;font-size:9px;font-weight:700;letter-spacing:1px;">{titulo}</div>
              <div style="color:{color};font-size:22px;font-weight:900;margin-top:4px;">{valor}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Barras por categoría
    categorias = [
        ('estrella',   '⭐', 'Pick Estrella'),
        ('mas_seguro', '🛡️', 'Pick Más Seguro'),
        ('segura',     '🛡️', 'Estrategia Segura'),
        ('moderada',   '⚖️', 'Estrategia Moderada'),
        ('arriesgada', '🔥', 'Estrategia Arriesgada'),
    ]
    html_bars = ""
    for key, emoji, label in categorias:
        s   = stats[key]
        pct = s['porcentaje']
        col = '#22c55e' if (pct or 0)>=60 else '#f59e0b' if (pct or 0)>=40 else '#ef4444'
        pct_txt = f"{pct}%" if pct is not None else "Sin datos"
        bw  = pct if pct is not None else 0
        sub = f"({s['acertados']}/{s['con_resultado']})" if s['con_resultado']>0 else "(sin resultados)"
        html_bars += f"""
        <div style="margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
            <span style="color:#cbd5e1;font-size:12px;font-weight:700;">{emoji} {label}</span>
            <div>
              <span style="color:#6b7280;font-size:10px;margin-right:6px;">{sub}</span>
              <span style="color:{col};font-size:13px;font-weight:900;">{pct_txt}</span>
            </div>
          </div>
          <div style="background:#1e293b;border-radius:4px;height:8px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,{col},{col}99);width:{bw}%;height:100%;border-radius:4px;transition:width 0.4s;"></div>
          </div>
        </div>"""
    st.markdown(f'<div style="background:#0d1117;border:1px solid #2d3748;border-radius:12px;padding:16px;">{html_bars}</div>',
                unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# APP UI — CONFIGURACIÓN
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
  label,.stTextInput label,.stTextArea label { color:#8b949e !important; font-size:12px !important; font-weight:600 !important; }
  .stTextInput input,.stTextArea textarea { background:#161c2b !important; color:#e1e1e1 !important; border:1px solid #2d3748 !important; border-radius:10px !important; font-size:13px !important; }
  [data-testid="stSelectbox"]>div>div { background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:10px !important; color:#e1e1e1 !important; }
  [data-testid="stExpander"] { background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:12px !important; }
  [data-testid="stExpanderToggleIcon"] svg { fill:#00e676 !important; }
  .stButton>button { background:linear-gradient(90deg,#00e676,#00b4d8) !important; border:none !important; border-radius:12px !important; color:#0d1117 !important; font-weight:800 !important; font-size:14px !important; width:100% !important; padding:0.65em !important; }
  .stButton>button:hover { opacity:.9; }
  .stButton>button:disabled { background:#2d3748 !important; color:#6b7280 !important; cursor:default !important; }
  .btn-actualizar>button { background:#2d3748 !important; color:#e1e1e1 !important; font-size:12px !important; margin-top:25px !important; }
  .btn-guardar>button { background:linear-gradient(90deg,#8b5cf6,#6366f1) !important; }
  .btn-danger>button { background:#ef444420 !important; color:#ef4444 !important; border:1px solid #ef444440 !important; }
  [data-testid="stAlert"] { border-radius:12px !important; }
  hr { border-color:#2d3748 !important; }
  [data-testid="stTabs"] button { background-color:#161c2b !important; color:#8b949e !important; font-weight:700 !important; border-radius:8px !important; border:1px solid #2d3748 !important; padding:6px 16px !important; margin-right:8px !important; }
  [data-testid="stTabs"] button[aria-selected="true"] { background-color:#00e67615 !important; color:#00e676 !important; border:1px solid #00e676 !important; }
  div[role="radiogroup"] { gap:8px; flex-wrap:wrap; margin-bottom:10px; }
  div[role="radiogroup"]>label { background:#161c2b !important; border:1px solid #2d3748 !important; border-radius:20px !important; padding:8px 16px !important; cursor:pointer; }
  div[role="radiogroup"]>label[data-checked="true"] { background:#00e67615 !important; border-color:#00e676 !important; }
  div[role="radiogroup"]>label span[data-baseweb="radio"] { display:none !important; }
  div[role="radiogroup"]>label p { font-size:13px !important; color:#8b949e !important; font-weight:600 !important; margin:0 !important; }
  div[role="radiogroup"]>label[data-checked="true"] p { color:#00e676 !important; }
  [data-testid="stCheckbox"] { background:#161c2b; padding:10px 14px; border-radius:8px; border:1px solid #2d3748; margin-bottom:5px; }
  [data-testid="stCheckbox"] label p { color:#e1e1e1 !important; font-size:14px !important; }
</style>
""", unsafe_allow_html=True)

# ─── SECRETS / CLAVES ───────────────────────────────────────────
try:
    secret_gemini   = st.secrets.get("GEMINI_API","")
    secret_odds     = st.secrets.get("ODDS_API","")
    secret_football = st.secrets.get("FOOTBALL_API","")
except FileNotFoundError:
    secret_gemini = secret_odds = secret_football = ""

api_gemini_ss = secret_gemini   or st.session_state.get("_gem","")
api_odds_ss   = secret_odds     or st.session_state.get("_odd","")
api_foot_ss   = secret_football or st.session_state.get("_foot","")

online = bool(api_gemini_ss and api_odds_ss)
bcol   = "#22c55e" if online else "#ef4444"
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;background:#161c2b;padding:13px 16px;border-radius:14px;margin-bottom:16px;border:1px solid #2d3748;">
  <span style="font-size:20px;font-weight:900;color:#e1e1e1;">BET<span style="color:#00e676;">⚡</span>COMBINADAS</span>
  <span style="border:1px solid {bcol};color:{bcol};font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;">{'🟢 EN LÍNEA' if online else '🔴 SIN CONEXIÓN'}</span>
</div>""", unsafe_allow_html=True)

with st.expander("⚙️ Configuración — Claves API", expanded=not online):
    if secret_gemini and secret_odds and secret_football:
        st.success("✅ Claves cargadas de forma permanente.")
        api_gemini=secret_gemini; api_odds=secret_odds; api_football=secret_football
    else:
        c1,c2,c3=st.columns(3)
        with c1: api_gemini=st.text_input("Gemini API",type="password",key="_gem")
        with c2: api_odds=st.text_input("Odds API",type="password",key="_odd")
        with c3: api_football=st.text_input("Football API",type="password",key="_foot")

# ─── TABS PRINCIPALES ────────────────────────────────────────────
tab_analisis, tab_historial = st.tabs(["🎯 Análisis", "📊 Historial & Stats"])

# ═══════════════════════════════════════════════════════════════
# TAB 1 — ANÁLISIS EN VIVO
# ═══════════════════════════════════════════════════════════════
with tab_analisis:
    # Liga
    st.markdown("<p style='color:#8b949e;font-size:12px;font-weight:600;margin-bottom:5px;margin-top:10px;'>🏆 Elige la Competición</p>", unsafe_allow_html=True)
    col_liga, col_btn = st.columns([4,1])
    with col_liga:
        liga_label = st.radio("Liga", list(LIGAS.keys()), horizontal=True, label_visibility="collapsed")
        liga = LIGAS[liga_label]
    with col_btn:
        st.markdown('<div class="btn-actualizar">', unsafe_allow_html=True)
        if st.button("🔄 Refrescar"):
            if api_odds_ss: obtener_partidos_api.clear(liga, api_odds_ss); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Cargar partidos
    upcoming_matches = []
    if api_odds_ss:
        resp, _ = obtener_partidos_api(liga, api_odds_ss)
        if isinstance(resp, list) and len(resp)>0:
            upcoming_matches = sorted(resp, key=lambda x: x.get('commence_time',''))[:6]

    st.markdown("---")
    st.subheader("🎯 Selecciona los partidos")
    selected_matches = []

    if upcoming_matches:
        partidos_por_dia = {}
        for p in upcoming_matches:
            fs = fmt_fecha(p['commence_time']); dia=fs.split(" · ")[0]; hora=fs.split(" · ")[1]
            if dia not in partidos_por_dia: partidos_por_dia[dia]=[]
            partidos_por_dia[dia].append((p,hora))

        for dia,lista in partidos_por_dia.items():
            st.markdown(f"<div style='background:#1e293b;padding:6px 12px;border-radius:6px;color:#93c5fd;font-weight:800;font-size:13px;margin-top:16px;margin-bottom:8px;border-left:4px solid #3b82f6;'>📅 {dia}</div>", unsafe_allow_html=True)
            for p,hora in lista:
                home_es=TRADUCCIONES.get(p['home_team'],p['home_team'])
                away_es=TRADUCCIONES.get(p['away_team'],p['away_team'])
                if st.toggle(f"⚽ **{home_es} vs {away_es}** *(🕒 {hora})*", key=p.get('id',p['home_team']+p['commence_time'])):
                    selected_matches.append(p)

        if selected_matches:
            st.markdown("<br>### 📊 Análisis del Mercado", unsafe_allow_html=True)
            for i,p in enumerate(selected_matches):
                st.markdown(render_simplified_card(p,i+1), unsafe_allow_html=True)
    else:
        if api_odds_ss and isinstance(resp,dict) and "message" in resp:
            st.error(f"❌ {resp['message']}")
        elif api_odds_ss:
            st.warning("⚠️ Sin partidos disponibles para esta liga. Prueba otra competición.")
        else:
            st.info("Ingresa tus claves API para ver los partidos.")

    # ── BOTÓN ALGORITMO ─────────────────────────────────────────
    st.markdown("---")
    if st.button("🚀 Ejecutar Algoritmo Quant (Análisis Automático)"):
        if not api_gemini_ss: st.error("❌ Falta la Gemini API Key.")
        elif not selected_matches: st.error("❌ Activa al menos un partido.")
        else:
            formatted_matches = []; partidos_ids = []
            with st.spinner("⏳ Cruzando estadísticas con cuotas del mercado..."):
                for p in selected_matches:
                    h2h,t_over,t_under,otros = extraer_odds(p)
                    home_es = TRADUCCIONES.get(p['home_team'],p['home_team'])
                    away_es = TRADUCCIONES.get(p['away_team'],p['away_team'])
                    partidos_ids.append(f"{home_es}-{away_es}")
                    stats_f = obtener_estadisticas_futbol(home_es,away_es,api_foot_ss) if api_foot_ss else {}
                    formatted_matches.append({
                        "local":home_es,"visita":away_es,
                        "fecha":fmt_fecha(p['commence_time'],simple=True),
                        "estadisticas_reales_equipo":stats_f,
                        "cuotas_1x2":h2h,"goles_over":t_over,"goles_under":t_under,
                        "otros_mercados":otros
                    })

            id_comb = ",".join(sorted(partidos_ids))
            prompt = f"""
Eres un Analista Cuantitativo Deportivo de élite. Tu misión es identificar selecciones GANADORAS y RENTABLES.

Competición: {liga_label}
Datos completos (cuotas reales + estadísticas):
{json.dumps(formatted_matches, ensure_ascii=False, indent=2)}

══════════════════════════════════════════════════
METODOLOGÍA OBLIGATORIA — 3 PASOS POR CADA PICK
══════════════════════════════════════════════════
🔍 PASO 1 – DIAGNÓSTICO DEPORTIVO: Forma reciente (W/D/L), posición en tabla, goles a favor/contra, ventaja local/visita.
📊 PASO 2 – LECTURA DEL MERCADO: ¿La cuota implícita (1/cuota) subestima la probabilidad real? ¿Hay +EV?
✅ PASO 3 – VEREDICTO GANADOR: ¿Por qué ocurrirá? ¿Cuál es el riesgo real? ¿Vale la relación riesgo/ganancia?

PICKS ESPECIALES OBLIGATORIOS:
⭐ PICK ESTRELLA: Mayor valor esperado (+EV) + mayor respaldo estadístico. Puede ser de cuota baja o media.
🛡️ PICK MÁS SEGURO: Mayor probabilidad de ocurrir. Prioriza certeza sobre rentabilidad.

MERCADOS DISPONIBLES: 1X2 | Doble Oportunidad (1X/X2/12) | Over/Under Goles | Ambos Anotan | Hándicap Asiático

REGLAS DE CUOTA:
🛡️ Segura: @1.15–@1.40 (1-2 picks) | ⚖️ Moderada: @2.35–@4.20 (2-4 picks) | 🔥 Arriesgada: @4.25–@8.95 (3-7 picks)

Responde ÚNICAMENTE con este JSON (sin markdown, sin texto extra):
{{
  "game_script": "Análisis táctico basado en los datos reales.",
  "pick_estrella": {{
    "partido":"Local vs Visita","seleccion":"Mercado","cuota":"X.XX","nivel_confianza":"Alta",
    "razonamiento":"PASO 1 [Diagnóstico]: ... PASO 2 [Mercado]: ... PASO 3 [Veredicto]: ..."
  }},
  "pick_mas_seguro": {{
    "partido":"Local vs Visita","seleccion":"Mercado","cuota":"X.XX","probabilidad_estimada":"XX%",
    "razonamiento":"Por qué es el más seguro según los datos."
  }},
  "estrategias": [
    {{"nivel":"🛡️ La Apuesta Segura (Protección de Bankroll)","picks":[{{"partido":"L vs V","seleccion":"Mercado","cuota":"X.XX","razonamiento_pick":"PASO 1:... PASO 2:... PASO 3:..."}}],"cuota_total":"X.XX","justificacion":"..."}},
    {{"nivel":"⚖️ La Apuesta Moderada (+EV Balanceado)","picks":[{{"partido":"L vs V","seleccion":"Mercado","cuota":"X.XX","razonamiento_pick":"PASO 1:... PASO 2:... PASO 3:..."}}],"cuota_total":"X.XX","justificacion":"..."}},
    {{"nivel":"🔥 La Apuesta Arriesgada (Ineficiencia de Mercado)","picks":[{{"partido":"L vs V","seleccion":"Mercado","cuota":"X.XX","razonamiento_pick":"PASO 1:... PASO 2:... PASO 3:..."}}],"cuota_total":"X.XX","justificacion":"..."}}
  ]
}}"""

            data = None
            with st.spinner("🧠 El algoritmo está razonando pick a pick..."):
                try:
                    data = obtener_analisis_ia(api_gemini_ss, prompt, id_comb)
                except Exception as e:
                    em = str(e)
                    if "429" in em or "quota" in em.lower(): st.warning("⏳ Límite de consultas alcanzado. Espera 1 minuto.")
                    elif "503" in em: st.warning("⏳ Servidores de Google saturados. Reintenta en segundos.")
                    else: st.error(f"❌ Error IA: {e}")

            if data:
                # Guardar en session_state para persistir entre reruns
                st.session_state.last_analysis = {
                    'data': data, 'liga': liga_label, 'id_comb': id_comb,
                    'partidos_str': json.dumps([{"local":m["local"],"visita":m["visita"]} for m in formatted_matches], ensure_ascii=False)
                }
                st.session_state.ticket_saved   = False
                st.session_state.saved_ticket_id = None

    # ── RENDERIZADO DEL ANÁLISIS (fuera del botón para persistir) ──
    if st.session_state.get('last_analysis'):
        data        = st.session_state.last_analysis['data']
        liga_label_ = st.session_state.last_analysis['liga']

        st.markdown("### 📈 El Veredicto del Algoritmo")

        # Banner calibración histórica
        hist_stats = calcular_estadisticas_db()
        if hist_stats and hist_stats['total']>0:
            cal_parts = []
            for key,emoji,short in [('segura','🛡️','Segura'),('moderada','⚖️','Moderada'),('arriesgada','🔥','Arriesgada')]:
                p = hist_stats[key]['porcentaje']
                if p is not None:
                    col_c = '#22c55e' if p>=60 else '#f59e0b' if p>=40 else '#ef4444'
                    cal_parts.append(f'<span style="color:{col_c};font-weight:800;">{emoji}{short}&nbsp;{p}%</span>')
            if cal_parts:
                st.markdown(f"""
                <div style="background:#0d1117;border:1px solid #2d3748;border-radius:8px;padding:8px 14px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                  <span style="color:#8b949e;font-size:10px;font-weight:700;">📊 CALIBRACIÓN HISTÓRICA · {hist_stats['total']} tickets</span>
                  <span style="font-size:11px;display:flex;gap:12px;">{''.join(cal_parts)}</span>
                </div>""", unsafe_allow_html=True)

        # Game Script
        st.markdown(f"""
        <div style="background:#0d1117;border-left:4px solid #8b5cf6;padding:14px 16px;border-radius:8px;margin-bottom:20px;">
          <div style="color:#a78bfa;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">⚡ Game Script</div>
          <div style="font-size:14px;color:#e1e1e1;line-height:1.5;"><i>"{data.get('game_script','')}"</i></div>
        </div>""", unsafe_allow_html=True)

        # Picks Destacados
        pick_e = data.get('pick_estrella',{})
        pick_s = data.get('pick_mas_seguro',{})
        if pick_e or pick_s:
            st.markdown("<div style='color:#8b949e;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;'>🏆 PICKS DESTACADOS DEL DÍA</div>", unsafe_allow_html=True)
            ce, cs = st.columns(2)
            with ce:
                if pick_e:
                    conf  = pick_e.get('nivel_confianza','Alta')
                    ccol  = '#22c55e' if conf=='Alta' else '#f59e0b' if conf=='Media' else '#ef4444'
                    st.markdown(f"""
                    <div style="background:linear-gradient(145deg,#1c1400,#0d1117);border:2px solid #f59e0b;border-radius:14px;padding:16px;min-height:160px;box-shadow:0 0 20px rgba(245,158,11,0.1);">
                      <div style="color:#f59e0b;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">⭐ PICK ESTRELLA</div>
                      <div style="color:#fef3c7;font-size:11px;opacity:.8;">{pick_e.get('partido','')}</div>
                      <div style="color:#fff;font-size:14px;font-weight:800;margin:4px 0 12px;">{pick_e.get('seleccion','')}</div>
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="background:#f59e0b;color:#0d1117;padding:5px 14px;border-radius:8px;font-weight:900;font-size:17px;">@{pick_e.get('cuota','')}</span>
                        <span style="border:1px solid {ccol};color:{ccol};padding:3px 8px;border-radius:10px;font-size:10px;font-weight:800;">🎯 {conf}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
            with cs:
                if pick_s:
                    prob = pick_s.get('probabilidad_estimada','?%')
                    st.markdown(f"""
                    <div style="background:linear-gradient(145deg,#001a0d,#0d1117);border:2px solid #22c55e;border-radius:14px;padding:16px;min-height:160px;box-shadow:0 0 20px rgba(34,197,94,0.1);">
                      <div style="color:#22c55e;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">🛡️ MÁS SEGURO</div>
                      <div style="color:#dcfce7;font-size:11px;opacity:.8;">{pick_s.get('partido','')}</div>
                      <div style="color:#fff;font-size:14px;font-weight:800;margin:4px 0 12px;">{pick_s.get('seleccion','')}</div>
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="background:#22c55e;color:#0d1117;padding:5px 14px;border-radius:8px;font-weight:900;font-size:17px;">@{pick_s.get('cuota','')}</span>
                        <span style="border:1px solid #22c55e;color:#22c55e;padding:3px 8px;border-radius:10px;font-size:10px;font-weight:800;">📊 {prob}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)

            # Razonamientos expandibles
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            re_, rs_ = st.columns(2)
            with re_:
                if pick_e.get('razonamiento'):
                    with st.expander("🧠 Análisis Estrella"):
                        r = (pick_e['razonamiento']
                             .replace('PASO 1','<b style="color:#f59e0b">🔍 PASO 1</b>')
                             .replace('PASO 2','<b style="color:#f59e0b">📊 PASO 2</b>')
                             .replace('PASO 3','<b style="color:#f59e0b">✅ PASO 3</b>'))
                        st.markdown(f'<div style="background:#1c1400;padding:12px;border-radius:8px;color:#cbd5e1;font-size:12px;line-height:1.6;border:1px solid #f59e0b30;">{r}</div>', unsafe_allow_html=True)
            with rs_:
                if pick_s.get('razonamiento'):
                    with st.expander("🧠 Análisis Más Seguro"):
                        st.markdown(f'<div style="background:#001a0d;padding:12px;border-radius:8px;color:#cbd5e1;font-size:12px;line-height:1.6;border:1px solid #22c55e30;">{pick_s["razonamiento"]}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div style='color:#8b949e;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;'>📊 ESTRATEGIAS POR NIVEL DE RIESGO</div>", unsafe_allow_html=True)

        # Estrategias con razonamiento por pick
        tabs_est = st.tabs(["🛡️ Segura","⚖️ Moderada","🔥 Arriesgada"])
        for i, tab in enumerate(tabs_est):
            with tab:
                est = data['estrategias'][i]
                picks_html = ""
                for pick in est['picks']:
                    raz = pick.get('razonamiento_pick','')
                    raz_blk = ""
                    if raz:
                        raz_f = (raz.replace('PASO 1','<b style="color:#818cf8">🔍 PASO 1</b>')
                                    .replace('PASO 2','<b style="color:#818cf8">📊 PASO 2</b>')
                                    .replace('PASO 3','<b style="color:#818cf8">✅ PASO 3</b>'))
                        raz_blk = f'<div style="background:#0a0f1e;padding:10px;border-radius:6px;border-left:3px solid #8b5cf6;margin-top:8px;"><span style="color:#a78bfa;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">🧠 Razonamiento</span><p style="color:#94a3b8;font-size:12px;line-height:1.55;margin:5px 0 0;">{raz_f}</p></div>'
                    picks_html += f"""
<div style="background:#0f172a;padding:12px;border-radius:10px;margin-bottom:10px;border:1px solid #1e293b;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="flex:1;padding-right:10px;">
      <span style="color:#8b949e;font-size:11px;font-weight:700;">⚽ {pick['partido']}</span>
      <div style="color:#e1e1e1;font-size:14px;font-weight:700;margin-top:2px;">{pick['seleccion']}</div>
    </div>
    <span style="background:#10b981;color:#0f172a;padding:5px 12px;border-radius:7px;font-weight:900;font-size:14px;">@{pick['cuota']}</span>
  </div>{raz_blk}
</div>"""
                st.markdown(f"""
<div style="background:#161c2b;border:2px dashed #2d3748;border-radius:12px;padding:16px;margin-top:8px;">
  <h4 style="color:#f8fafc;margin-top:0;border-bottom:1px solid #2d3748;padding-bottom:10px;margin-bottom:16px;">{est['nivel']}</h4>
  {picks_html}
  <div style="display:flex;justify-content:flex-end;margin:16px 0;">
    <div style="background:#8b5cf615;border:1px solid #8b5cf6;padding:8px 16px;border-radius:8px;">
      <span style="color:#c4b5fd;font-size:12px;font-weight:700;">CUOTA TOTAL:</span>
      <span style="color:#a78bfa;font-size:18px;font-weight:900;margin-left:8px;">@{est['cuota_total']}</span>
    </div>
  </div>
  <div style="background:#1e293b;padding:12px;border-radius:8px;border-left:3px solid #f59e0b;">
    <span style="color:#fcd34d;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">Tesis Cuantitativa (+EV)</span>
    <p style="color:#cbd5e1;font-size:13px;line-height:1.5;margin-top:6px;margin-bottom:0;">{est['justificacion']}</p>
  </div>
</div>""", unsafe_allow_html=True)

        # ── BOTÓN GUARDAR TICKET ───────────────────────────────────
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if not st.session_state.get('ticket_saved', False):
            st.markdown('<div class="btn-guardar">', unsafe_allow_html=True)
            if st.button("💾 Guardar este Ticket en el Historial"):
                an = st.session_state.last_analysis
                tid = guardar_ticket_db(
                    liga=an['liga'],
                    partidos_str=an['partidos_str'],
                    game_script=data.get('game_script',''),
                    pick_estrella=data.get('pick_estrella',{}),
                    pick_mas_seguro=data.get('pick_mas_seguro',{}),
                    estrategias=data.get('estrategias',[])
                )
                st.session_state.ticket_saved    = True
                st.session_state.saved_ticket_id = tid
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            tid = st.session_state.get('saved_ticket_id','?')
            st.success(f"✅ Ticket #{tid} guardado. Ve a la pestaña **📊 Historial & Stats** para marcar el resultado.")

    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TAB 2 — HISTORIAL & ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════════
with tab_historial:
    st.markdown("### 📊 Rendimiento Histórico del Algoritmo")

    hist_stats = calcular_estadisticas_db()
    render_stats_dashboard(hist_stats)

    st.markdown("---")
    st.markdown("### 🗂️ Tickets Registrados")

    historial = cargar_historial_db()
    if not historial:
        st.markdown("""
        <div style="text-align:center;padding:30px;color:#4b5563;">
          <div style="font-size:40px;margin-bottom:10px;">📭</div>
          <div>Aún no tienes tickets guardados.</div>
          <div style="font-size:12px;margin-top:4px;">Genera un análisis en la pestaña 🎯 Análisis y presiona "Guardar Ticket".</div>
        </div>""", unsafe_allow_html=True)
    else:
        for t in historial:
            render_ticket_historial(t)

    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
