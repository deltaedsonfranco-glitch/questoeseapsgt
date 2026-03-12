import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import time
import plotly.express as px

# 1. CONFIGURAÇÃO DE IDENTIDADE E ESTILO PROFISSIONAL
st.set_page_config(page_title="ESTRATÉGIA GABARITO - Oficial", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    button, .stButton>button, .streamlit-expanderHeader, [data-baseweb="select"], .stRadio label { cursor: pointer !important; }
    .question-box { background: #fdfdfd; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 15px; }
    .status-badge { font-weight: bold; font-size: 0.8em; padding: 3px 8px; border-radius: 5px; }
    .concluido { color: #28a745; border: 1px solid #28a745; background-color: #f0fff4; }
    .pendente { color: #888; border: 1px solid #888; }
    .check-assunto { background-color: #e8f5e9; padding: 15px; border-radius: 10px; border-left: 6px solid #2e7d32; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# CONFIGURAÇÕES TÉCNICAS (SGT: Use o link da SUA planilha abaixo e nos Secrets)
MINHA_URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1bV86Twi_Mm4mgMOzoyZFdncEmgud4rAzP9lSvmnCYUM/edit"
URL_BRASAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Bras%C3%A3o_da_PMMG.svg/1200px-Bras%C3%A3o_da_PMMG.svg.png"

# CONEXÃO SEGURA COM O GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ Falha crítica na configuração dos Secrets do Streamlit.")
    st.stop()

# --- FUNÇÃO DE REGISTRO EM BANCO DE DADOS (LOGS) ---
def registrar_log(aba, dados):
    try:
        # Lê sem cache para evitar duplicidade ou erro de leitura
        df_atual = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet=aba, ttl=0)
        df_novo = pd.concat([df_atual, pd.DataFrame([dados])], ignore_index=True)
        conn.update(spreadsheet=MINHA_URL_PLANILHA, worksheet=aba, data=df_novo)
        st.toast(f"Progresso salvo em {aba}! ✅")
    except Exception as e:
        st.error(f"Erro ao salvar na aba {aba}. Verifique se a aba existe na planilha.")

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'autenticado' not in st.session_state: 
    st.session_state.autenticado = False
    st.session_state.usuario = ""

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown('<div style="text-align:center; padding-top: 50px;">', unsafe_allow_html=True)
    st.image(URL_BRASAO, width=100)
    st.title("ESTRATÉGIA GABARITO")
    st.subheader("🛡️ Operação 3º Sargento")
    
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        u_input = st.text_input("Usuário PM:").strip().lower()
        p_input = st.text_input("Senha:", type="password").strip()
        
        if st.button("INICIAR MISSÃO"):
            try:
                # Tentativa de leitura da aba Usuarios
                df_u = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Usuarios", ttl=0)
                
                # Normalização de dados para busca
                u_login = u_input
                u_senha = p_input
                
                # Busca o Sgt na lista (Coluna 0 = Login, Coluna 1 = Senha)
                usuario_valido = False
                for i, row in df_u.iterrows():
                    if str(row.iloc[0]).strip().lower() == u_login and str(row.iloc[1]).strip() == u_senha:
                        usuario_valido = True
                        break
                
                if usuario_valido:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u_login
                    st.success("Acesso Autorizado! Carregando QG...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Login ou senha não conferem.")
            except Exception as e:
                st.error("⚠️ O Robô não conseguiu ler a planilha.")
                st.info(f"Verifique se o e-mail 'site-eap@qg-eap-dados.iam.gserviceaccount.com' está como EDITOR na sua planilha.")
                st.warning(f"Erro Técnico: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- CARREGAR HISTÓRICOS (Para marcação de feitos) ---
try:
    df_hist_q = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Log_Progresso", ttl=0)
    df_hist_a = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet="Assuntos_Estudados", ttl=0)
except:
    df_hist_q = pd.DataFrame()
    df_hist_a = pd.DataFrame()

# --- SIDEBAR E NAVEGAÇÃO ---
st.sidebar.image(URL_BRASAO, width=60)
st.sidebar.title(f"Sgt {st.session_state.usuario.upper()}")
menu = st.sidebar.radio("Navegação Principal:", ["📝 Simulado", "📊 Performance", "🚪 Sair"])

if menu == "🚪 Sair":
    st.session_state.autenticado = False
    st.rerun()

# --- MODO SIMULADO ---
if menu == "📝 Simulado":
    area = st.sidebar.selectbox("Área do Edital:", ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"])
    
    try:
        df_q = conn.read(spreadsheet=MINHA_URL_PLANILHA, worksheet=area, ttl="2m")
        
        if not df_q.empty:
            # Colunas L(11) e M(12)
            lista_leis = sorted([x for x in df_q.iloc[:, 11].unique() if str(x).strip() != '' and str(x) != 'nan'])
            sel_lei = st.selectbox("🎯 1. Selecione a Lei ou Manual:", lista_leis)
            
            df_f_lei = df_q[df_q.iloc[:, 11] == sel_lei]
            lista_titulos = sorted([x for x in df_f_lei.iloc[:, 12].unique() if str(x).strip() != '' and str(x) != 'nan'])
            sel_titulo = st.selectbox(f"📖 2. Selecione o Título de {sel_lei}:", ["VER TODOS"] + lista_titulos)

            # --- MARCAÇÃO DE TÓPICO COMO ESTUDADO ---
            if sel_titulo != "VER TODOS":
                id_assunto = f"{sel_lei} - {sel_titulo}"
                ja_estudou = False
                if not df_hist_a.empty:
                    ja_estudou = not df_hist_a[(df_hist_a['Usuario'] == st.session_state.usuario) & (df_hist_a['Topico'] == id_assunto)].empty
                
                if ja_estudou:
                    st.markdown(f'<div class="check-assunto">✅ Você já marcou este tópico como ESTUDADO.</div>', unsafe_allow_html=True)
                else:
                    if st.button(f"🏁 Marcar '{sel_titulo}' como Estudado"):
                        registrar_log("Assuntos_Estudados", {
                            "Usuario": st.session_state.usuario, "Materia": sel_lei, 
                            "Topico": id_assunto, "Status": "Concluído", "Data": datetime.datetime.now().strftime("%d/%m/%Y")
                        })
                        st.rerun()

            st.divider()

            # --- EXIBIÇÃO DAS QUESTÕES ---
            df_exibir = df_f_lei if sel_titulo == "VER TODOS" else df_f_lei[df_f_lei.iloc[:, 12] == sel_titulo]
            
            minhas_questoes = []
            if not df_hist_q.empty:
                minhas_questoes = df_hist_q[df_hist_q['Usuario'] == st.session_state.usuario]['Questao'].tolist()

            for i, row in df_exibir.iterrows():
                q_id = str(row.iloc[0])
                ja_fez = q_id in minhas_questoes
                badge = '<span class="status-badge concluido">RESOLVIDA</span>' if ja_fez else '<span class="status-badge pendente">PENDENTE</span>'
                
                with st.container():
                    st.markdown(f'<div class="question-box"><b>QUESTÃO {q_id}</b> {badge}<br><br>{row.iloc[3]}</div>', unsafe_allow_html=True)
                    
                    # Alternativas A(4) a D(7)
                    ops = {"A": row.iloc[4], "B": row.iloc[5], "C": row.iloc[6], "D": row.iloc[7]}
                    ops_v = {k: v for k, v in ops.items() if str(v).strip() != '' and str(v).lower() != 'nan'}
                    
                    escolha = st.radio(f"Selecione a resposta (Q{q_id}):", list(ops_v.values()), key=f"r_{q_id}")
                    
                    if st.button(f"Validar Q{q_id}", key=f"b_{q_id}"):
                        letra = [l for l, t in ops_v.items() if t == escolha][0]
                        gab = str(row.iloc[8]).strip().upper()
                        status = "Acerto" if letra == gab else "Erro"
                        
                        registrar_log("Log_Progresso", {
                            "Usuario": st.session_state.usuario, "Materia": sel_lei, "Titulo": sel_titulo,
                            "Questao": q_id, "Status": status, "Data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                        
                        if status == "Acerto": st.success("🎯 Correto! Alvo batido.")
                        else: st.error(f"❌ Errou! Gabarito: {gab}")
                        st.info(f"💡 Dica Técnica: {row.iloc[9]}")
    except Exception as e:
        st.error(f"Erro ao carregar aba {area}. Verifique se a aba existe na planilha.")

# --- MODO PERFORMANCE ---
elif menu == "📊 Performance":
    st.header("📊 Inteligência de Desempenho")
    if not df_hist_q.empty:
        meu_h = df_hist_q[df_hist_q['Usuario'] == st.session_state.usuario]
        if not meu_h.empty:
            c1, c2 = st.columns(2)
            total = len(meu_h)
            acertos = len(meu_h[meu_h['Status'] == 'Acerto'])
            c1.metric("Total Resolvido", total)
            c2.metric("Aproveitamento", f"{(acertos/total*100):.1f}%")
            
            fig = px.pie(names=['Acertos', 'Erros'], values=[acertos, total-acertos], 
                         color_discrete_sequence=['#28a745', '#dc3545'], hole=.4)
            st.plotly_chart(fig)
        else: st.info("Sem dados de questões para este usuário.")
    else: st.info("O banco de dados de progresso está vazio.")
