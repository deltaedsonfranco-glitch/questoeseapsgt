import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import time
import plotly.graph_objects as go

# ═══════════════════════════════════════════════════════════════
#  CONSTANCY — EAP 3º SGT PM 2026 | BANCA CRS | PMMG
#
#  LÓGICA DE RASTREAMENTO DE QUESTÕES (sem colisão):
#
#  O Log_Progresso possui a coluna "Ref" = Materia + "_" + Questao
#  Ex: "Direito Penal Militar_5" ou "EMEMG_81"
#
#  Como cada Materia é única em todo o banco (EMEMG só existe na
#  Institucional, Direito Penal Militar só na Jurídica, etc.),
#  a Ref é um identificador global sem nenhuma colisão possível.
#
#  O session_state também usa a Ref como chave:
#  status_q_EMEMG_81  /  status_q_Direito Penal Militar_5
#  → nunca confunde questões de abas diferentes.
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CONSTANCY · EAP 2026",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── ESTILOS ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(160deg, #0a1628 0%, #0f2040 40%, #0a1628 100%);
    min-height: 100vh;
}

.stApp p, .stApp span, .stApp div, .stApp li { color: #e2e8f0; }
.stMarkdown, .stMarkdown p { color: #e2e8f0 !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06111e 0%, #0d1f38 100%) !important;
    border-right: 1px solid rgba(200,168,75,0.25) !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stRadio label {
    padding: 10px 14px; border-radius: 8px; transition: 0.2s; cursor: pointer; display: block;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(200,168,75,0.12) !important; }

.brand-header {
    text-align: center; padding: 10px 0 6px 0;
    border-bottom: 1px solid rgba(200,168,75,0.3); margin-bottom: 10px;
}
.brand-title {
    font-family: 'Bebas Neue', sans-serif; font-size: 2.1rem; letter-spacing: 4px;
    background: linear-gradient(135deg, #c8a84b, #f0d078, #c8a84b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; line-height: 1; margin: 0;
}
.brand-sub { font-size: 0.68rem; letter-spacing: 3px; color: #94a3b8 !important; text-transform: uppercase; margin-top: 2px; }

.card-questao {
    background: rgba(20,40,80,0.92);
    border: 1px solid rgba(255,255,255,0.15);
    border-left: 4px solid #3b82f6;
    border-radius: 12px; padding: 22px 26px 16px 26px;
    margin-bottom: 6px; backdrop-filter: blur(8px); transition: border-color 0.3s;
}
.card-questao.resolvida { border-left-color: #c8a84b; }

.q-numero {
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 1px; color: #60a5fa; text-transform: uppercase;
    margin-bottom: 8px; display: flex; align-items: center; gap: 10px;
}
.q-texto { font-size: 1rem !important; line-height: 1.75 !important; color: #f1f5f9 !important; font-weight: 400; }

.badge { display: inline-block; font-size: 0.65rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; padding: 3px 10px; border-radius: 20px; }
.badge-pendente  { background: rgba(148,163,184,0.15); color: #94a3b8; border: 1px solid rgba(148,163,184,0.3); }
.badge-resolvida { background: rgba(200,168,75,0.15);  color: #c8a84b; border: 1px solid rgba(200,168,75,0.35); }

.feedback-box { border-radius: 10px; padding: 14px 18px; margin-top: 12px; font-size: 0.9rem; font-weight: 500; }
.feedback-acerto { background: rgba(22,163,74,0.12);  border: 1px solid rgba(22,163,74,0.3);  color: #4ade80; }
.feedback-erro   { background: rgba(220,38,38,0.10);  border: 1px solid rgba(220,38,38,0.3);  color: #f87171; }
.feedback-info   { background: rgba(37,99,235,0.10);  border: 1px solid rgba(37,99,235,0.3);  color: #93c5fd; margin-top: 8px; }
.feedback-warn   { background: rgba(234,179,8,0.10);  border: 1px solid rgba(234,179,8,0.3);  color: #fde047; margin-top: 8px; }

.metric-card {
    background: rgba(20,40,80,0.92); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 14px; padding: 20px 24px; text-align: center;
}
.metric-valor { font-family: 'Bebas Neue', sans-serif; font-size: 2.8rem; letter-spacing: 2px; color: #c8a84b; line-height: 1; }
.metric-label { font-size: 0.72rem; letter-spacing: 2px; color: #64748b; text-transform: uppercase; margin-top: 4px; }

.secao-titulo {
    font-family: 'Bebas Neue', sans-serif; font-size: 1.5rem;
    letter-spacing: 3px; color: #f1f5f9;
    border-bottom: 2px solid rgba(200,168,75,0.4);
    padding-bottom: 6px; margin: 24px 0 16px 0;
}

/* INPUTS — fundo branco, texto PRETO */
.stTextInput > div > div > input,
input[type="text"],
input[type="password"],
input[type="email"] {
    background: #ffffff !important;
    border: 1.5px solid #c8a84b !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    caret-color: #0f172a !important;
    padding: 10px 14px !important;
}
input[type="text"]::placeholder, input[type="password"]::placeholder { color: #94a3b8 !important; }
input { background: #ffffff !important; color: #0f172a !important; }
.stTextInput label { color: #94a3b8 !important; font-size: 0.78rem !important; letter-spacing: 1px !important; text-transform: uppercase !important; }

.stSelectbox > div > div { background: rgba(255,255,255,0.08) !important; border-color: rgba(200,168,75,0.35) !important; color: #f1f5f9 !important; border-radius: 8px !important; }
.stSelectbox label { color: #94a3b8 !important; font-size: 0.78rem !important; letter-spacing: 1px !important; text-transform: uppercase !important; }

.stRadio > div { gap: 6px !important; }
.stRadio label {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important; padding: 12px 16px !important;
    color: #f1f5f9 !important; transition: all 0.2s !important; cursor: pointer;
}
.stRadio label:hover { background: rgba(37,99,235,0.1) !important; border-color: rgba(37,99,235,0.3) !important; }

.stButton > button {
    background: linear-gradient(135deg, #1e40af, #2563eb) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; letter-spacing: 1px !important; text-transform: uppercase !important;
    font-size: 0.78rem !important; padding: 10px 20px !important; transition: all 0.2s !important;
    box-shadow: 0 4px 15px rgba(37,99,235,0.3) !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(37,99,235,0.45) !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #854d0e, #c8a84b) !important; }

.streamlit-expanderHeader { background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; color: #94a3b8 !important; }

hr { border-color: rgba(200,168,75,0.15) !important; margin: 20px 0 !important; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #06111e; }
::-webkit-scrollbar-thumb { background: rgba(200,168,75,0.3); border-radius: 3px; }

.login-titulo {
    font-family: 'Bebas Neue', sans-serif; font-size: 3.5rem; letter-spacing: 8px;
    background: linear-gradient(135deg, #c8a84b, #f0d078, #c8a84b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; text-align: center; line-height: 1; margin: 0;
}
.login-subtitulo { font-size: 0.78rem; letter-spacing: 4px; color: #64748b; text-transform: uppercase; text-align: center; margin-top: 4px; margin-bottom: 32px; }
.login-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(200,168,75,0.2); border-radius: 16px; padding: 32px 36px; backdrop-filter: blur(10px); }

.barra-container { margin: 6px 0 16px 0; }
.barra-label { display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; }
.barra-track { width: 100%; height: 8px; background: rgba(255,255,255,0.06); border-radius: 100px; overflow: hidden; }
.barra-fill { height: 100%; border-radius: 100px; background: linear-gradient(90deg, #1d4ed8, #3b82f6); }
.barra-fill.alta  { background: linear-gradient(90deg, #15803d, #22c55e); }
.barra-fill.media { background: linear-gradient(90deg, #b45309, #f59e0b); }

.btn-whatsapp {
    display: block; width: 100%; background: linear-gradient(135deg, #128C7E, #25D366);
    color: white !important; text-align: center; padding: 13px; border-radius: 10px;
    text-decoration: none; font-weight: 700; margin-top: 16px; letter-spacing: 1px;
    font-size: 0.85rem; box-shadow: 0 4px 15px rgba(37,211,102,0.25); transition: 0.3s; text-transform: uppercase;
}
.btn-whatsapp:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(37,211,102,0.4); }
</style>
""", unsafe_allow_html=True)


# ─── CONEXÃO ────────────────────────────────────────────────────
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    MINHA_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("⚠️ Erro nos Secrets (.streamlit/secrets.toml)")
    st.stop()


# ─── FUNÇÕES UTILITÁRIAS ─────────────────────────────────────────

def limpar_dados(df):
    """Normaliza nomes de colunas duplicadas e remove espaços em strings."""
    if df is None or df.empty:
        return pd.DataFrame()
    colunas = [str(c).strip() for c in df.columns]
    vistos, novas = {}, []
    for c in colunas:
        if c in vistos:
            vistos[c] += 1
            novas.append(f"{c}_{vistos[c]}")
        else:
            vistos[c] = 0
            novas.append(c)
    df.columns = novas
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    return df


def montar_ref(materia, questao_id):
    """
    Cria a chave de referência única: Materia_ID
    Ex.: 'Direito Penal Militar_5'  /  'EMEMG_81'
    Essa chave é usada tanto no Log_Progresso (coluna Ref)
    quanto nas chaves do session_state — sem nenhuma colisão
    entre abas, pois cada Materia pertence a uma única aba.
    """
    mat = str(materia).strip()
    qid = str(questao_id).split('.')[0].strip()
    return f"{mat}_{qid}"


def registrar_log(dados):
    """Salva uma linha no Log_Progresso incluindo a coluna Ref."""
    try:
        df_atual = conn.read(spreadsheet=MINHA_URL, worksheet="Log_Progresso", ttl=0)
        df_novo  = pd.concat([df_atual, pd.DataFrame([dados])], ignore_index=True)
        conn.update(spreadsheet=MINHA_URL, worksheet="Log_Progresso", data=df_novo)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


def validar_questao_callback(ref, radio_key, ops, gabarito,
                              explicacao, pegadinha, materia, topico,
                              questao_id, usuario):
    """
    Callback do botão Validar.
    Grava no log com a coluna Ref = Materia_ID.
    Salva resultado no session_state usando a mesma Ref como chave.
    """
    escolha = st.session_state[radio_key]
    letra   = [l for l, t in ops.items() if t == escolha][0]
    status  = "Acerto" if letra == str(gabarito).strip().upper() else "Erro"

    registrar_log({
        "Usuario": usuario,
        "Materia": materia,
        "Titulo":  topico,
        "Questao": questao_id,
        "Status":  status,
        "Data":    datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Ref":     ref,          # ← coluna G: identificador sem colisão
    })

    # Persiste na sessão atual usando a Ref como chave
    st.session_state[f"status_q_{ref}"] = status
    st.session_state[f"gab_q_{ref}"]    = gabarito
    st.session_state[f"exp_q_{ref}"]    = explicacao
    st.session_state[f"pega_q_{ref}"]   = pegadinha


def reset_materia(usuario, materia_alvo):
    """Zera histórico de uma matéria específica do usuário."""
    try:
        for aba_nome in ["Assuntos_Estudados", "Log_Progresso"]:
            df   = conn.read(spreadsheet=MINHA_URL, worksheet=aba_nome, ttl=0)
            df_n = limpar_dados(df.copy())
            col_u = next((c for c in df_n.columns if 'usuario' in c.lower()), df_n.columns[0])
            col_m = next((c for c in df_n.columns if 'materia' in c.lower()), df_n.columns[1])
            mask  = ~((df_n[col_u].str.lower() == usuario.lower()) & (df_n[col_m] == materia_alvo))
            conn.update(spreadsheet=MINHA_URL, worksheet=aba_nome, data=df[mask])
        st.cache_data.clear()
        st.success(f"✅ Progresso de '{materia_alvo}' zerado com sucesso!")
        time.sleep(1.5)
        st.rerun()
    except Exception as e:
        st.error(f"Erro no Reset: {e}")


def barra_progresso(label, valor, maximo):
    pct = min(100, int(valor / maximo * 100)) if maximo > 0 else 0
    cor = "alta" if pct >= 70 else ("media" if pct >= 40 else "")
    return f"""
    <div class="barra-container">
        <div class="barra-label"><span>{label}</span><span>{valor}/{maximo} ({pct}%)</span></div>
        <div class="barra-track"><div class="barra-fill {cor}" style="width:{pct}%"></div></div>
    </div>"""


# ─── SESSION STATE ───────────────────────────────────────────────
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False


# ════════════════════════════════════════════════════════════════
#  TELA DE LOGIN
# ════════════════════════════════════════════════════════════════
if not st.session_state.autenticado:

    st.markdown("""
    <div style="text-align:center; padding-top:50px;">
        <div style="font-size:72px; filter:drop-shadow(0 0 20px rgba(200,168,75,0.4));">🎯</div>
        <p class="login-titulo">CONSTANCY</p>
        <p class="login-subtitulo">EAP · 3º Sgt PM · 2026 · Banca CRS · PMMG</p>
    </div>
    """, unsafe_allow_html=True)

    _, col_c, _ = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center; font-size:1.4rem; margin-bottom:12px; opacity:0.6;">⚔️ 🛡️ 🏆</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            u_input = st.text_input("Usuário ou E-mail").strip().lower()
            p_input = st.text_input("Senha", type="password").strip()
            submit  = st.form_submit_button("▶  Iniciar Missão", use_container_width=True)

            if submit:
                df_u = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Usuarios", ttl="5m"))
                if not df_u.empty:
                    col_usu = next((c for c in df_u.columns if 'usuario'  in c.lower()), df_u.columns[0])
                    col_sen = next((c for c in df_u.columns if 'senha'    in c.lower()), df_u.columns[1])
                    col_val = next((c for c in df_u.columns if 'validade' in c.lower()
                                    or 'expiracao' in c.lower()), None)
                    user_row = df_u[df_u[col_usu].str.lower() == u_input]

                    if not user_row.empty and str(user_row.iloc[0][col_sen]) == p_input:
                        acesso_ok = True
                        if col_val:
                            lim_str = str(user_row.iloc[0][col_val]).strip()
                            if lim_str.lower() not in ['nan', 'none', '']:
                                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                                    try:
                                        lim = datetime.datetime.strptime(lim_str[:10], fmt).date()
                                        if datetime.date.today() > lim:
                                            acesso_ok = False
                                        break
                                    except ValueError:
                                        continue
                        if acesso_ok:
                            st.cache_data.clear()
                            st.session_state.autenticado = True
                            st.session_state.usuario     = u_input
                            st.rerun()
                        else:
                            st.error("⏳ Acesso expirado. Entre em contato para renovar.")
                    else:
                        st.error("❌ Usuário ou senha inválidos.")

        NUM = "5535999999999"   # ← altere para o seu número
        MSG = "Olá! Quero adquirir o acesso ao CONSTANCY — EAP 3º Sgt PM 2026."
        st.markdown(f"""
        <a href="https://wa.me/{NUM}?text={MSG.replace(' ','%20')}" target="_blank" class="btn-whatsapp">
            💬  Adquirir Acesso / Suporte
        </a>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# ════════════════════════════════════════════════════════════════
#  DADOS GLOBAIS
# ════════════════════════════════════════════════════════════════
df_hist_q = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Log_Progresso",      ttl="2m"))
df_hist_a = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Assuntos_Estudados", ttl="2m"))
nome_exibir = st.session_state.usuario.split('@')[0].upper()

# Pré-computa o conjunto de Refs já resolvidas pelo usuário atual
# usando a coluna G (Ref = Materia_ID) — identificador sem colisão
refs_resolvidas_banco: set = set()
if not df_hist_q.empty:
    col_u_g = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
    df_meu_g = df_hist_q[df_hist_q[col_u_g].str.lower() == st.session_state.usuario]

    # Tenta usar a coluna Ref (col G) — disponível na planilha atualizada
    if 'Ref' in df_meu_g.columns:
        refs_resolvidas_banco = set(df_meu_g['Ref'].dropna().str.strip().tolist())
    else:
        # Fallback: reconstrói a Ref a partir de Materia + Questao
        # para compatibilidade com logs antigos sem a coluna Ref
        col_m_g = next((c for c in df_meu_g.columns if 'materia' in c.lower()), df_meu_g.columns[1])
        col_q_g = next((c for c in df_meu_g.columns if 'questao' in c.lower()), df_meu_g.columns[3])
        refs_resolvidas_banco = set(
            montar_ref(row[col_m_g], row[col_q_g])
            for _, row in df_meu_g.iterrows()
        )


# ════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div class="brand-header">
        <p class="brand-title">CONSTANCY</p>
        <p class="brand-sub">EAP · 3º Sgt PM · 2026</p>
    </div>
    <div style="text-align:center; padding: 10px 0 16px 0;">
        <div style="font-size:2rem;">🎖️</div>
        <div style="font-size:0.78rem; color:#c8a84b; font-weight:700; letter-spacing:2px;">{nome_exibir}</div>
        <div style="font-size:0.65rem; color:#475569; margin-top:2px;">COMBATENTE · BANCA CRS</div>
    </div>
    """, unsafe_allow_html=True)

    menu = st.radio(
        "nav",
        ["📝  Simulado", "📊  Performance", "📚  Teoria", "🚪  Sair"],
        label_visibility="collapsed"
    )

    # Stats rápidas
    if not df_hist_q.empty:
        col_u_sb = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
        col_s_sb = next((c for c in df_hist_q.columns if 'status'  in c.lower()), df_hist_q.columns[4])
        meu_sb   = df_hist_q[df_hist_q[col_u_sb].str.lower() == st.session_state.usuario]
        total_sb   = len(meu_sb)
        acertos_sb = len(meu_sb[meu_sb[col_s_sb] == 'Acerto'])
        taxa_sb    = round(acertos_sb / total_sb * 100, 1) if total_sb > 0 else 0.0
        st.markdown(f"""
        <div style="border-top:1px solid rgba(200,168,75,0.2); margin-top:16px; padding-top:16px;">
            <div style="font-size:0.65rem; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Progresso Geral</div>
            <div style="text-align:center; font-family:'Bebas Neue',sans-serif; font-size:1.8rem; color:#c8a84b; letter-spacing:2px;">{taxa_sb}%</div>
            <div style="text-align:center; font-size:0.65rem; color:#475569; letter-spacing:2px;">TAXA DE ACERTO</div>
            <div style="text-align:center; font-size:0.75rem; color:#64748b; margin-top:4px;">{total_sb} questões feitas</div>
        </div>
        """, unsafe_allow_html=True)

if menu == "🚪  Sair":
    st.session_state.autenticado = False
    st.cache_data.clear()
    st.rerun()


# ════════════════════════════════════════════════════════════════
#  SIMULADO
# ════════════════════════════════════════════════════════════════
if menu == "📝  Simulado":

    st.markdown('<p class="secao-titulo">⚔️  CAMPO DE TREINAMENTO</p>', unsafe_allow_html=True)

    AREAS = {
        "Legislacao_Institucional": "🏛️  Legislação Institucional",
        "Doutrina_Operacional":     "🎯  Doutrina Operacional",
        "Legislacao_Juridica":      "⚖️  Legislação Jurídica",
    }

    area = st.selectbox("Área do Edital", list(AREAS.keys()), format_func=lambda x: AREAS[x])

    try:
        df_q = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet=area, ttl="2m"))

        if df_q.empty:
            st.warning("Nenhuma questão encontrada nesta área.")
            st.stop()

        # Garante que há colunas suficientes
        while df_q.shape[1] < 13:
            df_q[f"coluna_{df_q.shape[1]}"] = ""

        col_id       = df_q.columns[0]   # ID numérico da questão
        col_pergunta = df_q.columns[3]   # Enunciado
        col_gab      = df_q.columns[8]   # Gabarito (A/B/C/D)
        col_exp      = df_q.columns[9]   # Explicação
        col_pega     = df_q.columns[10]  # Pegadinha CRS
        col_mat      = df_q.columns[11]  # Matéria (ex: "EMEMG", "Direito Penal Militar")
        col_topico   = df_q.columns[12]  # Tópico/Título

        leis = sorted([x for x in df_q[col_mat].unique() if str(x).lower() not in ['nan', '']])
        c1, c2 = st.columns(2)
        with c1:
            sel_lei = st.selectbox("Disciplina", leis)
        df_f = df_q[df_q[col_mat] == sel_lei]

        titulos = sorted([x for x in df_f[col_topico].unique() if str(x).lower() not in ['nan', '']])
        with c2:
            sel_titulo = st.selectbox("Tópico", ["📋  VER TODOS"] + titulos)

        # ── Marcar tópico como estudado ────────────────────────
        if sel_titulo != "📋  VER TODOS":
            id_topico   = f"{sel_lei} - {sel_titulo}"
            ja_estudado = False
            if not df_hist_a.empty:
                col_ua   = next((c for c in df_hist_a.columns if 'usuario' in c.lower()), df_hist_a.columns[0])
                col_tops = [c for c in df_hist_a.columns if 'topico' in c.lower()]
                df_ua    = df_hist_a[df_hist_a[col_ua].str.lower() == st.session_state.usuario]
                for c in col_tops:
                    if id_topico.strip() in [str(x).strip() for x in df_ua[c].tolist()]:
                        ja_estudado = True
                        break

            if ja_estudado:
                st.markdown('<div class="feedback-box feedback-acerto">✅  Tópico marcado como <b>ESTUDADO</b> — bom trabalho, combatente!</div>', unsafe_allow_html=True)
            else:
                if st.button("🏁  Marcar Tópico como Estudado"):
                    registrar_log({   # reusa registrar_log mas grava em outra aba
                        "Usuario": st.session_state.usuario,
                        "Materia": sel_lei,
                        "Topico":  id_topico,
                        "Status":  "Concluído",
                        "Data":    datetime.datetime.now().strftime("%d/%m/%Y")
                    })
                    # Para esta operação específica usa a aba Assuntos_Estudados
                    try:
                        df_at = conn.read(spreadsheet=MINHA_URL, worksheet="Assuntos_Estudados", ttl=0)
                        novo  = {"Usuario": st.session_state.usuario, "Materia": sel_lei,
                                 "Topico": id_topico, "Status": "Concluído",
                                 "Data": datetime.datetime.now().strftime("%d/%m/%Y")}
                        conn.update(spreadsheet=MINHA_URL, worksheet="Assuntos_Estudados",
                                    data=pd.concat([df_at, pd.DataFrame([novo])], ignore_index=True))
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao marcar tópico: {e}")

        st.divider()

        df_exibir = df_f if sel_titulo == "📋  VER TODOS" else df_f[df_f[col_topico] == sel_titulo]

        # ── Barra de progresso do bloco ─────────────────────────
        total_bloco  = len(df_exibir)
        feitas_bloco = sum(
            1 for _, r in df_exibir.iterrows()
            if montar_ref(r[col_mat], r[col_id]) in refs_resolvidas_banco
            or f"status_q_{montar_ref(r[col_mat], r[col_id])}" in st.session_state
        )
        st.markdown(barra_progresso("Progresso neste bloco", feitas_bloco, total_bloco), unsafe_allow_html=True)

        # ── Renderiza cada questão ──────────────────────────────
        for _, row in df_exibir.iterrows():
            # ref é o identificador único global desta questão
            ref = montar_ref(row[col_mat], row[col_id])
            q_id_limpo = str(row[col_id]).split('.')[0].strip()

            feita_banco  = ref in refs_resolvidas_banco
            feita_agora  = f"status_q_{ref}" in st.session_state
            ja_resolvida = feita_banco or feita_agora

            badge_html = (
                '<span class="badge badge-resolvida">✓ Resolvida</span>'
                if ja_resolvida else
                '<span class="badge badge-pendente">○ Pendente</span>'
            )
            card_class = "card-questao resolvida" if ja_resolvida else "card-questao"

            st.markdown(f"""
            <div class="{card_class}">
                <div class="q-numero">Q{q_id_limpo} {badge_html}</div>
                <div class="q-texto">{row[col_pergunta]}</div>
            </div>
            """, unsafe_allow_html=True)

            ops    = {"A": row.iloc[4], "B": row.iloc[5], "C": row.iloc[6], "D": row.iloc[7]}
            opcoes = [v for v in ops.values() if str(v).lower() != 'nan' and str(v).strip() != '']

            # Chave do widget usa a Ref — sem colisão entre abas
            st.radio(
                f"Resposta Q{q_id_limpo}:",
                opcoes,
                key=f"r_{ref}",
                label_visibility="collapsed",
                disabled=ja_resolvida
            )

            if not ja_resolvida:
                topico_log = row[col_topico] if sel_titulo == "📋  VER TODOS" else sel_titulo
                st.button(
                    f"Validar Resposta — Q{q_id_limpo}",
                    key=f"b_{ref}",
                    use_container_width=True,
                    on_click=validar_questao_callback,
                    args=(ref, f"r_{ref}", ops, row[col_gab],
                          row[col_exp], row[col_pega],
                          str(row[col_mat]).strip(), topico_log,
                          q_id_limpo, st.session_state.usuario)
                )
            else:
                if feita_agora:
                    status = st.session_state[f"status_q_{ref}"]
                    if status == "Acerto":
                        st.markdown('<div class="feedback-box feedback-acerto">🎯  ACERTOU! Excelente raciocínio tático.</div>', unsafe_allow_html=True)
                    else:
                        gab = st.session_state[f"gab_q_{ref}"]
                        st.markdown(f'<div class="feedback-box feedback-erro">❌  ERROU! Gabarito correto: <b>Alternativa {gab}</b></div>', unsafe_allow_html=True)
                    exp = str(st.session_state[f"exp_q_{ref}"]).strip()
                    if exp.lower() not in ['nan', 'none', '']:
                        st.markdown(f'<div class="feedback-box feedback-info">💡  <b>Comentário:</b> {exp}</div>', unsafe_allow_html=True)
                    pega = str(st.session_state[f"pega_q_{ref}"]).strip()
                    if pega.lower() not in ['nan', 'none', '']:
                        st.markdown(f'<div class="feedback-box feedback-warn">🚨  <b>Pegadinha CRS:</b> {pega}</div>', unsafe_allow_html=True)
                else:
                    with st.expander("Ver Gabarito e Comentários"):
                        st.markdown(f"**Gabarito:** {row[col_gab]}")
                        exp = str(row[col_exp]).strip()
                        if exp.lower() not in ['nan', 'none', '']:
                            st.markdown(f'<div class="feedback-box feedback-info">💡  {exp}</div>', unsafe_allow_html=True)
                        pega = str(row[col_pega]).strip()
                        if pega.lower() not in ['nan', 'none', '']:
                            st.markdown(f'<div class="feedback-box feedback-warn">🚨  {pega}</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro no Simulado: {e}")


# ════════════════════════════════════════════════════════════════
#  PERFORMANCE
# ════════════════════════════════════════════════════════════════
elif menu == "📊  Performance":

    col_h1, col_h2 = st.columns([3, 1])
    col_h1.markdown('<p class="secao-titulo">📊  INTELIGÊNCIA DE PERFORMANCE</p>', unsafe_allow_html=True)
    if col_h2.button("🔄  Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if df_hist_q.empty:
        st.info("Nenhum dado encontrado. Resolva questões para ver sua performance.")
        st.stop()

    col_uhu = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
    meu_h   = df_hist_q[df_hist_q[col_uhu].str.lower() == st.session_state.usuario].copy()

    if meu_h.empty:
        st.warning("Nenhum dado sincronizado. Resolva questões e atualize.")
        st.stop()

    col_s   = next((c for c in meu_h.columns if 'status' in c.lower()), meu_h.columns[4])
    acertos = len(meu_h[meu_h[col_s] == 'Acerto'])
    total_q = len(meu_h)
    taxa    = acertos / total_q * 100

    # ── Métricas ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-valor">{total_q}</div><div class="metric-label">Questões Feitas</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-valor">{acertos}</div><div class="metric-label">Acertos</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-valor">{taxa:.1f}%</div><div class="metric-label">Taxa de Acerto</div></div>', unsafe_allow_html=True)
    with c4:
        status_op = "OPERACIONAL" if taxa >= 70 else "TREINAMENTO"
        cor_op    = "#4ade80"     if taxa >= 70 else "#f59e0b"
        st.markdown(f'<div class="metric-card"><div class="metric-valor" style="color:{cor_op};font-size:1.4rem;">{status_op}</div><div class="metric-label">Status</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cobertura do Edital ──────────────────────────────────────
    st.markdown('<p class="secao-titulo" style="font-size:1.1rem;">🎯 Cobertura do Edital</p>', unsafe_allow_html=True)
    banco_total = []
    for a in ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"]:
        df_t = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet=a, ttl="5m"))
        if not df_t.empty:
            while df_t.shape[1] < 12:
                df_t[f"pad_{df_t.shape[1]}"] = ""
            resumo = df_t.iloc[:, [0, 11]].copy()
            resumo.columns = ['id_q', 'materia_q']
            resumo = resumo[(resumo['materia_q'].str.lower() != 'nan') & (resumo['materia_q'] != '')]
            banco_total.append(resumo)

    df_p = pd.DataFrame()
    if banco_total:
        df_banco  = pd.concat(banco_total)
        total_mat = df_banco.groupby('materia_q').size().reset_index(name='Total')
        col_m     = next((c for c in meu_h.columns if 'materia' in c.lower()), meu_h.columns[1])
        feito_mat = meu_h.groupby(col_m).size().reset_index(name='Feito')
        df_p = pd.merge(total_mat, feito_mat, left_on='materia_q', right_on=col_m, how='left').fillna(0)
        df_p['Perc'] = (df_p['Feito'] / df_p['Total']) * 100
        df_p = df_p.sort_values('Perc', ascending=False)

        for _, rw in df_p.iterrows():
            st.markdown(barra_progresso(rw['materia_q'], int(rw['Feito']), int(rw['Total'])), unsafe_allow_html=True)

        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(
            y=df_p['materia_q'], x=df_p['Perc'], orientation='h',
            marker=dict(color=df_p['Perc'],
                        colorscale=[[0,'#1e3a5f'],[0.5,'#2563eb'],[1,'#22c55e']],
                        showscale=False),
            text=df_p['Perc'].apply(lambda x: f"<b>{x:.0f}%</b>"),
            textposition='inside',
            hovertemplate='%{y}: %{x:.1f}%<extra></extra>'
        ))
        fig_p.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            height=max(300, len(df_p) * 38),
            xaxis=dict(range=[0,100], dtick=20, gridcolor='rgba(255,255,255,0.06)',
                       tickfont=dict(color='#475569', size=11)),
            yaxis=dict(tickfont=dict(color='#94a3b8', size=12)),
            margin=dict(l=200, r=20, t=20, b=20),
            font=dict(family='Inter')
        )
        st.plotly_chart(fig_p, use_container_width=True)

    # ── Constância diária ────────────────────────────────────────
    st.markdown('<p class="secao-titulo" style="font-size:1.1rem;">📅 Constância de Estudos</p>', unsafe_allow_html=True)
    col_d = next((c for c in meu_h.columns if 'data' in c.lower()), meu_h.columns[5])
    meu_h['Data_Limpa'] = pd.to_datetime(
        meu_h[col_d].astype(str).str.strip().str[:10],
        format='%d/%m/%Y', errors='coerce'
    )
    df_tempo = meu_h.dropna(subset=['Data_Limpa']).groupby('Data_Limpa').size().reset_index(name='Volume')
    df_tempo = df_tempo.sort_values('Data_Limpa')
    df_tempo['Dia'] = df_tempo['Data_Limpa'].dt.strftime('%d/%m')

    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=df_tempo['Dia'], y=df_tempo['Volume'],
        mode='lines+markers',
        line=dict(color='#c8a84b', width=2.5),
        marker=dict(size=7, color='#f0d078', line=dict(color='#854d0e', width=1.5)),
        fill='tozeroy', fillcolor='rgba(200,168,75,0.08)',
        hovertemplate='%{x}: <b>%{y} questões</b><extra></extra>'
    ))
    fig_t.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        height=250,
        xaxis=dict(gridcolor='rgba(255,255,255,0.04)', tickfont=dict(color='#475569')),
        yaxis=dict(gridcolor='rgba(255,255,255,0.04)', tickfont=dict(color='#475569')),
        margin=dict(l=40, r=20, t=10, b=40),
        font=dict(family='Inter')
    )
    st.plotly_chart(fig_t, use_container_width=True)

    # ── Reset de matéria ─────────────────────────────────────────
    st.divider()
    st.markdown('<p class="secao-titulo" style="font-size:1rem; color:#f87171;">🧹 Limpeza de Prontuário</p>', unsafe_allow_html=True)
    col_m_reset = next((c for c in meu_h.columns if 'materia' in c.lower()), meu_h.columns[1])
    mat_disp    = df_p['materia_q'].unique() if not df_p.empty else meu_h[col_m_reset].unique()
    m_reset     = st.selectbox("Selecione a matéria para zerar:", mat_disp)
    if st.button("⚠️  ZERAR HISTÓRICO DA MATÉRIA", type="primary"):
        reset_materia(st.session_state.usuario, m_reset)


# ════════════════════════════════════════════════════════════════
#  TEORIA
# ════════════════════════════════════════════════════════════════
elif menu == "📚  Teoria":

    st.markdown('<p class="secao-titulo">📚  BASE TEÓRICA — RESUMOS</p>', unsafe_allow_html=True)
    try:
        df_teoria = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Explicacoes_Teoria", ttl="5m"))
        if df_teoria.empty:
            st.info("Nenhum conteúdo teórico cadastrado ainda.")
        else:
            col_mat_t    = df_teoria.columns[0]
            col_cap      = df_teoria.columns[1]
            col_res      = df_teoria.columns[2]
            col_palavras = df_teoria.columns[3] if df_teoria.shape[1] > 3 else None
            col_ref_t    = df_teoria.columns[4] if df_teoria.shape[1] > 4 else None

            materias = sorted([x for x in df_teoria[col_mat_t].unique() if str(x).lower() not in ['nan', '']])
            sel_mat  = st.selectbox("Selecione a Matéria:", materias)
            df_tf    = df_teoria[df_teoria[col_mat_t] == sel_mat]

            for _, row in df_tf.iterrows():
                cap = str(row[col_cap]).strip()
                res = str(row[col_res]).strip()
                if res.lower() in ['nan', 'none', '']:
                    continue

                tags_html = ""
                if col_palavras:
                    palavras = str(row[col_palavras]).strip()
                    if palavras.lower() not in ['nan', 'none', '']:
                        for p in palavras.split(','):
                            tags_html += f'<span style="background:rgba(37,99,235,0.15);color:#93c5fd;padding:2px 8px;border-radius:20px;font-size:0.72rem;margin-right:4px;">{p.strip()}</span>'

                ref_html = ""
                if col_ref_t:
                    ref_val = str(row[col_ref_t]).strip()
                    if ref_val.lower() not in ['nan', 'none', '']:
                        ref_html = f'<div style="font-size:0.72rem;color:#c8a84b;margin-top:10px;">📌 Edital: {ref_val}</div>'

                st.markdown(f"""
                <div class="card-questao" style="margin-bottom:14px;">
                    <div class="q-numero">{cap}</div>
                    <div class="q-texto" style="margin-top:8px;">{res}</div>
                    <div style="margin-top:10px;">{tags_html}</div>
                    {ref_html}
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao carregar teoria: {e}")
