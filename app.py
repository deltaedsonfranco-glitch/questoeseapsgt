import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px
import time

# 1. CONFIGURAÇÃO DE IDENTIDADE
st.set_page_config(page_title="ESTRATÉGIA GABARITO - Oficial", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    button, .stButton>button, .streamlit-expanderHeader, [data-baseweb="select"], .stRadio label { cursor: pointer !important; }
    .question-box { background: #fdfdfd; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    .status-concluido { color: #28a745; font-weight: bold; font-size: 0.9em; border: 1px solid #28a745; padding: 2px 5px; border-radius: 5px; }
    .status-pendente { color: #888; font-weight: bold; font-size: 0.8em; }
    .assunto-estudado { background-color: #e8f5e9; padding: 10px; border-radius: 10px; border-left: 5px solid #2e7d32; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

MINHA_URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1bV86Twi_Mm4mgMOzoyZFdncEmgud4rAzP9lSvmnCYUM/edit"
URL_BRASAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Bras%C3%A3o_da_PMMG.svg/1200px-Bras%C3%A3o_da_PMMG.svg.png"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE BANCO DE DADOS ---
def registrar_no_banco(aba, dados_dict):
    try:
        df_total = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet=aba, ttl=0)
        nova_linha = pd.DataFrame([dados_dict])
        df_final = pd.concat([df_total, nova_linha], ignore_index=True)
        conn.update(spreadsheet=MINHA_URL_PLANILHA, worksheet=aba, data=df_final)
        st.toast("Progresso sincronizado com a nuvem! ☁️")
    except: st.error("Erro ao conectar com o banco de dados.")

def limpar_dados_usuario(usuario):
    try:
        # Limpa questões
        df_q = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", ttl=0)
        conn.update(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", data=df_q[df_q['Usuario'] != usuario])
        # Limpa assuntos
        df_a = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Assuntos_Estudados", ttl=0)
        conn.update(spreadsheet=MINHA_URL_PLANILHA, worksheet="Assuntos_Estudados", data=df_a[df_a['Usuario'] != usuario])
        st.success("Toda sua trajetória foi resetada.")
        time.sleep(1)
        st.rerun()
    except: pass

# --- LOGIN ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown('<div style="text-align:center; padding-top: 50px;">', unsafe_allow_html=True)
    st.image(URL_BRASAO, width=100)
    st.title("ESTRATÉGIA GABARITO")
    u_input = st.text_input("Usuário PM:").strip().lower()
    p_input = st.text_input("Senha:", type="password").strip()
    if st.button("INICIAR MISSÃO"):
        df_u = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Usuarios", ttl="1m")
        for i, r in df_u.iterrows():
            if str(r.iloc[0]).lower() == u_input and str(r.iloc[1]) == p_input:
                st.session_state.autenticado = True
                st.session_state.usuario = u_input
                st.rerun()
        st.error("Credenciais inválidas.")
    st.stop()

# --- CARREGAR HISTÓRICOS ---
df_hist_q = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", ttl=0)
df_hist_a = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Assuntos_Estudados", ttl=0)

meus_assuntos = []
if not df_hist_a.empty:
    meus_assuntos = df_hist_a[df_hist_a['Usuario'] == st.session_state.usuario]['Topico'].unique().tolist()

# --- INTERFACE ---
st.sidebar.title(f"Sgt {st.session_state.usuario.upper()}")
menu = st.sidebar.radio("Navegação:", ["📝 Simulado", "📊 Performance", "🚪 Sair"])

if menu == "🚪 Sair":
    st.session_state.autenticado = False
    st.rerun()

if menu == "📝 Simulado":
    area = st.sidebar.selectbox("Área do Edital:", ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"])
    df_q = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet=area, ttl="5m")
    
    if not df_q.empty:
        # Seleção macro
        lista_leis = sorted(df_q.iloc[:, 11].unique())
        sel_lei = st.selectbox("🎯 1. Selecione a Lei/Manual:", lista_leis)
        
        df_f_lei = df_q[df_q.iloc[:, 11] == sel_lei]
        lista_titulos = sorted(df_f_lei.iloc[:, 12].unique())
        sel_titulo = st.selectbox("📖 2. Selecione o Tópico:", ["VER TODOS"] + lista_titulos)

        # --- LOGICA DE MARCAÇÃO DE ASSUNTO ---
        if sel_titulo != "VER TODOS":
            identificador_assunto = f"{sel_lei} - {sel_titulo}"
            ja_estudou_assunto = identificador_assunto in meus_assuntos
            
            if ja_estudou_assunto:
                st.markdown(f'<div class="assunto-estudado">✅ Você já concluiu o estudo teórico deste tópico em momentos anteriores.</div>', unsafe_allow_html=True)
            else:
                if st.button(f"🏁 Marcar '{sel_titulo}' como Estudado"):
                    registrar_no_banco("Assuntos_Estudados", {
                        "Usuario": st.session_state.usuario,
                        "Materia": sel_lei,
                        "Topico": identificador_assunto,
                        "Status": "Concluído",
                        "Data": datetime.datetime.now().strftime("%d/%m/%Y")
                    })
                    st.rerun()

        # --- EXIBIÇÃO DAS QUESTÕES ---
        df_exibir = df_f_lei if sel_titulo == "VER TODOS" else df_f_lei[df_f_lei.iloc[:, 12] == sel_titulo]
        
        # Filtro de questões feitas pelo usuário
        minhas_questoes = []
        if not df_hist_q.empty:
            minhas_questoes = df_hist_q[df_hist_q['Usuario'] == st.session_state.usuario]['Questao'].tolist()

        for i, row in df_exibir.iterrows():
            q_id = str(row.iloc[0])
            status_q = "✅ RESOLVIDA" if q_id in minhas_questoes else "⏳ PENDENTE"
            
            with st.container():
                st.markdown(f'<div class="question-box"><b>QUESTÃO {q_id}</b> <span class="status-concluido" style="border:none;">{status_q}</span><br><br>{row.iloc[3]}</div>', unsafe_allow_html=True)
                ops = {"A": row.iloc[4], "B": row.iloc[5], "C": row.iloc[6], "D": row.iloc[7]}
                ops_v = {k: v for k, v in ops.items() if str(v) != "" and str(v).lower() != 'nan'}
                escolha = st.radio(f"Selecione a alternativa (Q{q_id}):", list(ops_v.values()), key=f"rad_{q_id}")
                
                if st.button(f"Validar Questão {q_id}", key=f"btn_{q_id}"):
                    letra = [l for l, t in ops_v.items() if t == escolha][0]
                    gab = str(row.iloc[8]).strip().upper()
                    status = "Acerto" if letra == gab else "Erro"
                    
                    registrar_no_banco("Log_Progresso", {
                        "Usuario": st.session_state.usuario, "Materia": sel_lei, "Titulo": sel_titulo,
                        "Questao": q_id, "Status": status, "Data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    
                    if status == "Acerto": st.success("🎯 Resposta Correta!")
                    else: st.error(f"❌ Resposta Incorreta. Gabarito: {gab}")
                    st.info(f"💡 Fundamentação: {row.iloc[9]}")

elif menu == "📊 Performance":
    st.header("📊 Seu Painel de Controle")
    # (Mesma lógica de gráficos anterior, mas incluindo os Assuntos Estudados)
    if not df_hist_a.empty:
        meus_assuntos_count = len(df_hist_a[df_hist_a['Usuario'] == st.session_state.usuario])
        st.metric("Tópicos do Edital Concluídos", meus_assuntos_count)
    
    if st.button("⚠️ ZERAR TODO MEU PROGRESSO (Cuidado)"):
        limpar_dados_usuario(st.session_state.usuario)
