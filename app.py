import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px
import time

# 1. CONFIGURAÇÃO DE IDENTIDADE E ESTILO
st.set_page_config(page_title="ESTRATÉGIA GABARITO - Ofical", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    button, .stButton>button, .streamlit-expanderHeader, [data-baseweb="select"], .stRadio label { cursor: pointer !important; }
    .question-box { background: #fdfdfd; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    .status-concluido { color: #28a745; font-weight: bold; font-size: 0.8em; }
    .status-pendente { color: #888; font-weight: bold; font-size: 0.8em; }
    </style>
""", unsafe_allow_html=True)

# Link da sua planilha
MINHA_URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1bV86Twi_Mm4mgMOzoyZFdncEmgud4rAzP9lSvmnCYUM/edit"
URL_BRASAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Bras%C3%A3o_da_PMMG.svg/1200px-Bras%C3%A3o_da_PMMG.svg.png"

# CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE BANCO DE DADOS ---
def registrar_no_banco(usuario, lei, titulo, q_id, status):
    try:
        df_atual = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", ttl=0)
        nova_linha = pd.DataFrame([{
            "Usuario": usuario, "Materia": lei, "Titulo": titulo,
            "Questao": str(q_id), "Status": status,
            "Data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        }])
        df_final = pd.concat([df_atual, nova_linha], ignore_index=True)
        conn.update(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", data=df_final)
        st.toast("Progresso Salvo! ✅")
    except: pass

def limpar_historico(usuario):
    try:
        df_total = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", ttl=0)
        # Mantém apenas os dados que NÃO são do usuário atual
        df_limpo = df_total[df_total['Usuario'] != usuario]
        conn.update(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", data=df_limpo)
        st.success("Seu histórico foi resetado com sucesso!")
        time.sleep(1)
        st.rerun()
    except: st.error("Erro ao limpar dados.")

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
        if not df_u.empty:
            for i, r in df_u.iterrows():
                if str(r.iloc[0]).lower() == u_input and str(r.iloc[1]) == p_input:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u_input
                    st.rerun()
        st.error("Dados incorretos.")
    st.stop()

# --- CARREGAR HISTÓRICO PARA MARCAÇÃO ---
df_historico = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", ttl=0)
questoes_feitas = []
if not df_historico.empty:
    questoes_feitas = df_historico[df_historico['Usuario'] == st.session_state.usuario]['Questao'].tolist()

# --- INTERFACE ---
st.sidebar.title(f"Sgt {st.session_state.usuario.upper()}")
menu = st.sidebar.radio("Navegação:", ["📝 Simulado", "📊 Performance", "🚪 Sair"])

if menu == "🚪 Sair":
    st.session_state.autenticado = False
    st.rerun()

# --- SIMULADO ---
if menu == "📝 Simulado":
    area = st.sidebar.selectbox("Área do Edital:", ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"])
    df_q = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet=area, ttl="5m")
    
    if not df_q.empty:
        lista_leis = sorted(df_q.iloc[:, 11].unique())
        sel_lei = st.selectbox("🎯 Lei ou Manual:", lista_leis)
        
        df_f_lei = df_q[df_q.iloc[:, 11] == sel_lei]
        lista_titulos = sorted(df_f_lei.iloc[:, 12].unique())
        sel_titulo = st.selectbox("📖 Tópico:", ["VER TODOS"] + lista_titulos)
        
        df_exibir = df_f_lei if sel_titulo == "VER TODOS" else df_f_lei[df_f_lei.iloc[:, 12] == sel_titulo]

        for i, row in df_exibir.iterrows():
            q_id = str(row.iloc[0])
            ja_fez = q_id in questoes_feitas
            label_status = "✅ CONCLUÍDA" if ja_fez else "⏳ PENDENTE"
            class_status = "status-concluido" if ja_fez else "status-pendente"

            with st.container():
                st.markdown(f'<div class="question-box"><b>Q{q_id}</b> <span class="{class_status}">{label_status}</span><br>{row.iloc[3]}</div>', unsafe_allow_html=True)
                
                ops = {"A": row.iloc[4], "B": row.iloc[5], "C": row.iloc[6], "D": row.iloc[7]}
                ops_v = {k: v for k, v in ops.items() if str(v) != "" and str(v).lower() != 'nan'}
                escolha = st.radio(f"Resposta Q{i}:", list(ops_v.values()), key=f"r_{q_id}")
                
                if st.button(f"Validar Q{q_id}", key=f"b_{q_id}"):
                    letra_sel = [l for l, t in ops_v.items() if t == escolha][0]
                    gab = str(row.iloc[8]).strip().upper()
                    status = "Acerto" if letra_sel == gab else "Erro"
                    
                    registrar_no_banco(st.session_state.usuario, sel_lei, sel_titulo, q_id, status)
                    if status == "Acerto": st.success("🎯 Acertou!")
                    else: st.error(f"❌ Errou! Gabarito: {gab}")
                    st.info(f"💡 Dica: {row.iloc[9]}")

# --- PERFORMANCE ---
elif menu == "📊 Performance":
    st.header("📊 Seu Painel de Performance")
    
    if not df_historico.empty:
        meu_hist = df_historico[df_historico['Usuario'] == st.session_state.usuario]
        
        if not meu_hist.empty:
            c1, c2 = st.columns(2)
            total = len(meu_hist)
            acertos = len(meu_hist[meu_hist['Status'] == 'Acerto'])
            erros = total - acertos
            
            c1.metric("Total Resolvido", total)
            c2.metric("Aproveitamento Geral", f"{(acertos/total*100):.1f}%")

            # Gráfico
            fig = px.pie(values=[acertos, erros], names=['Acerto', 'Erro'], 
                         color_discrete_sequence=['#28a745', '#dc3545'], hole=.4)
            st.plotly_chart(fig)
            
            st.divider()
            st.subheader("🧹 Zona de Reset")
            if st.button("LIMPAR TODO MEU HISTÓRICO"):
                limpar_historico(st.session_state.usuario)
        else:
            st.info("Você ainda não respondeu nenhuma questão.")
    else:
        st.info("O banco de dados está vazio.")
