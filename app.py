import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go

# 1. ESTILO E IDENTIDADE VISUAL
st.set_page_config(page_title="QG DO EAP - Inteligência", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .question-box {
        background-color: white; padding: 25px; border-radius: 15px;
        border-left: 8px solid #1e3a8a; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px; color: #1e293b;
    }
    .status-badge { font-weight: 700; font-size: 0.75rem; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; }
    .concluido { background-color: #dcfce7; color: #166534; }
    .pendente { background-color: #f1f5f9; color: #475569; }
    .ytick text { font-weight: bold !important; font-size: 14px !important; color: black !important; }
    </style>
""", unsafe_allow_html=True)

URL_BRASAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Bras%C3%A3o_da_PMMG.svg/1200px-Bras%C3%A3o_da_PMMG.svg.png"

# CONEXÃO
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    MINHA_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("⚠️ Erro nos Secrets (.streamlit/secrets.toml)")
    st.stop()

# --- FUNÇÃO DE LIMPEZA CIRÚRGICA ANTIDUPLICIDADE ---
def limpar_dados(df):
    if df is None or df.empty: return pd.DataFrame()
    
    colunas_limpas = [str(c).strip() for c in df.columns]
    colunas_sem_duplicidade = []
    contagem = {}
    for c in colunas_limpas:
        if c in contagem:
            contagem[c] += 1
            colunas_sem_duplicidade.append(f"{c}_{contagem[c]}")
        else:
            contagem[c] = 0
            colunas_sem_duplicidade.append(c)
            
    df.columns = colunas_sem_duplicidade

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    return df

# --- FUNÇÕES DE BANCO ---
def registrar_log(aba, dados):
    try:
        df_atual = conn.read(spreadsheet=MINHA_URL, worksheet=aba, ttl="10m")
        df_novo = pd.concat([df_atual, pd.DataFrame([dados])], ignore_index=True)
        conn.update(spreadsheet=MINHA_URL, worksheet=aba, data=df_novo)
        st.cache_data.clear()
        st.toast("Missão Registrada! ✅")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def reset_materia(usuario, materia_alvo):
    try:
        for aba in ["Assuntos_Estudados", "Log_Progresso"]:
            df = conn.read(spreadsheet=MINHA_URL, worksheet=aba, ttl="10m")
            df_n = limpar_dados(df)
            col_usu = next((c for c in df_n.columns if 'usuario' in c.lower()), df_n.columns[0])
            col_mat = next((c for c in df_n.columns if 'materia' in c.lower() or 'mat' in c.lower()), df_n.columns[1])
            
            mask = ~((df_n[col_usu].str.lower() == usuario.lower()) & (df_n[col_mat] == materia_alvo))
            conn.update(spreadsheet=MINHA_URL, worksheet=aba, data=df[mask])
            
        st.cache_data.clear()
        st.success(f"Progresso de '{materia_alvo}' foi zerado!")
        time.sleep(1.5); st.rerun()
    except Exception as e: st.error(f"Erro no Reset: {e}")

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# --- LOGIN ---
if not st.session_state.autenticado:
    st.markdown('<div style="text-align:center; padding-top: 50px;">', unsafe_allow_html=True)
    st.image(URL_BRASAO, width=120)
    st.title("ESTRATÉGIA GABARITO")
    with st.form("login"):
        u_input = st.text_input("Usuário PM:").strip().lower()
        p_input = st.text_input("Senha:", type="password").strip()
        if st.form_submit_button("INICIAR MISSÃO", use_container_width=True):
            df_u = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Usuarios", ttl="10m"))
            if not df_u.empty:
                col_usu = next((c for c in df_u.columns if 'usuario' in c.lower()), df_u.columns[0])
                col_sen = next((c for c in df_u.columns if 'senha' in c.lower()), df_u.columns[1])
                user_row = df_u[df_u[col_usu].str.lower() == u_input]
                if not user_row.empty and str(user_row.iloc[0][col_sen]) == p_input:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u_input
                    st.rerun()
                else: st.error("Acesso Negado. Verifique os dados.")
    st.stop()

# --- CARREGA HISTÓRICOS ---
df_hist_q = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Log_Progresso", ttl="10m"))
df_hist_a = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Assuntos_Estudados", ttl="10m"))

# --- NAVEGAÇÃO ---
st.sidebar.image(URL_BRASAO, width=80)
st.sidebar.markdown(f"### 🎖️ Sgt {st.session_state.usuario.upper()}")
menu = st.sidebar.radio("Quartel General:", ["📝 Simulado", "📊 Performance", "🚪 Sair"])

if menu == "🚪 Sair":
    st.session_state.autenticado = False
    st.rerun()

# --- SIMULADO (FILTROS L e M + COMENTÁRIOS) ---
if menu == "📝 Simulado":
    area = st.sidebar.selectbox("Área do Edital:", ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"])
    try:
        df_q = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet=area, ttl="10m"))
        if not df_q.empty:
            while df_q.shape[1] < 13:
                df_q[f"coluna_{df_q.shape[1]}"] = ""

            col_id = df_q.columns[0]
            col_pergunta = df_q.columns[3]
            col_gab = df_q.columns[8]
            col_exp = df_q.columns[9]     # Coluna J (Explicação)
            col_pega = df_q.columns[10]   # Coluna K (Pegadinha CRS)
            col_mat = df_q.columns[11]    # Coluna L
            col_topico = df_q.columns[12] # Coluna M
            
            leis = sorted([x for x in df_q[col_mat].unique() if str(x).lower() not in ['nan', '']])
            sel_lei = st.selectbox("🎯 Disciplina:", leis)
            
            df_f_lei = df_q[df_q[col_mat] == sel_lei]
            
            titulos = sorted([x for x in df_f_lei[col_topico].unique() if str(x).lower() not in ['nan', '']])
            sel_titulo = st.selectbox("📖 Tópico:", ["VER TUDO"] + titulos)

            if sel_titulo != "VER TUDO":
                id_a = f"{sel_lei} - {sel_titulo}"
                ja_estudado = False
                
                if not df_hist_a.empty:
                    col_usu_a = next((c for c in df_hist_a.columns if 'usuario' in c.lower()), df_hist_a.columns[0])
                    col_topicos = [c for c in df_hist_a.columns if 'topico' in c.lower()]
                    
                    df_user_a = df_hist_a[df_hist_a[col_usu_a].str.lower() == st.session_state.usuario]
                    for c in col_topicos:
                        if not df_user_a[df_user_a[c] == id_a].empty:
                            ja_estudado = True
                            break
                
                if ja_estudado:
                    st.success("✅ Tópico já marcado como ESTUDADO.")
                else:
                    if st.button("🏁 Marcar Tópico como Estudado", use_container_width=True):
                        registrar_log("Assuntos_Estudados", {
                            "Usuario": st.session_state.usuario,
                            "Materia": sel_lei,
                            "Topico": id_a,
                            "Status": "Concluído",
                            "Data": datetime.datetime.now().strftime("%d/%m/%Y")
                        })
                        st.rerun()
            st.divider()

            df_exibir = df_f_lei if sel_titulo == "VER TUDO" else df_f_lei[df_f_lei[col_topico] == sel_titulo]

            minhas_q = []
            if not df_hist_q.empty:
                col_usu_hist = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
                col_q_hist = next((c for c in df_hist_q.columns if 'questao' in c.lower()), df_hist_q.columns[3])
                minhas_q = df_hist_q[df_hist_q[col_usu_hist].str.lower() == st.session_state.usuario][col_q_hist].tolist()

            for i, row in df_exibir.iterrows():
                q_id = str(row[col_id])
                badge = '<span class="status-badge concluido">FEITA</span>' if q_id in minhas_q else '<span class="status-badge pendente">PENDENTE</span>'
                
                with st.container():
                    st.markdown(f'<div class="question-box"><b>Q{q_id}</b> {badge}<br><br>{row[col_pergunta]}</div>', unsafe_allow_html=True)
                    ops = {"A": row.iloc[4], "B": row.iloc[5], "C": row.iloc[6], "D": row.iloc[7]}
                    opcoes_validas = [v for v in ops.values() if str(v).lower() != 'nan' and str(v).strip() != '']
                    
                    escolha = st.radio(f"Res Q{q_id}:", opcoes_validas, key=f"r_{q_id}", label_visibility="collapsed")
                    
                    if st.button(f"Validar Q{q_id}", key=f"b_{q_id}", use_container_width=True):
                        letra = [l for l, t in ops.items() if t == escolha][0]
                        status = "Acerto" if letra == str(row[col_gab]).strip().upper() else "Erro"
                        
                        registrar_log("Log_Progresso", {
                            "Usuario": st.session_state.usuario, "Materia": sel_lei, 
                            "Titulo": row[col_topico] if sel_titulo == "VER TUDO" else sel_titulo, 
                            "Questao": q_id, "Status": status, "Data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                        
                        if status == "Acerto": st.success("🎯 ACERTOU!")
                        else: st.error(f"❌ ERROU! Gabarito: {row[col_gab]}")
                        
                        # --- EXIBIÇÃO DA EXPLICAÇÃO E PEGADINHA CRS ---
                        exp_texto = str(row[col_exp]).strip()
                        if exp_texto.lower() not in ['nan', 'none', '']:
                            st.info(f"💡 **Comentário:** {exp_texto}")
                            
                        pega_texto = str(row[col_pega]).strip()
                        if pega_texto.lower() not in ['nan', 'none', '']:
                            st.warning(f"🚨 **Alerta Pegadinha CRS:** {pega_texto}")
                            
    except Exception as e: st.error(f"Erro no Simulado: {e}")

# --- PERFORMANCE ---
elif menu == "📊 Performance":
    st.title("📊 Painel de Inteligência e Performance")
    
    if not df_hist_q.empty:
        col_usu_hist = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
        meu_h = df_hist_q[df_hist_q[col_usu_hist].str.lower() == st.session_state.usuario].copy()
        
        if meu_h.empty:
            st.warning("O seu usuário ainda não registrou respostas no banco de dados.")
        else:
            col_status = next((c for c in meu_h.columns if 'status' in c.lower()), meu_h.columns[4])
            acertos = len(meu_h[meu_h[col_status] == 'Acerto'])
            total_q = len(meu_h)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões Resolvidas", total_q)
            c2.metric("Taxa de Acerto", f"{(acertos/total_q*100):.1f}%")
            c3.metric("Status Global", "OPERACIONAL" if (acertos/total_q) >= 0.7 else "TREINAMENTO")

            st.subheader("🎯 Progresso no Edital (Cobertura 0-100%)")
            
            areas = ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"]
            banco_total = []
            for a in areas:
                df_temp = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet=a, ttl="10m"))
                if not df_temp.empty:
                    while df_temp.shape[1] < 12: 
                        df_temp[f"pad_{df_temp.shape[1]}"] = ""
                    
                    df_resumo = df_temp.iloc[:, [0, 11]].copy()
                    df_resumo.columns = ['id_q', 'materia_q']
                    df_resumo = df_resumo[(df_resumo['materia_q'].str.lower() != 'nan') & (df_resumo['materia_q'] != '')]
                    banco_total.append(df_resumo)
            
            if banco_total:
                df_banco = pd.concat(banco_total)
                total_mat = df_banco.groupby('materia_q').size().reset_index(name='Total')
                
                col_mat_hist = next((c for c in meu_h.columns if 'materia' in c.lower() or 'mat' in c.lower()), meu_h.columns[1])
                feito_mat = meu_h.groupby(col_mat_hist).size().reset_index(name='Feito')
                
                df_p = pd.merge(total_mat, feito_mat, left_on='materia_q', right_on=col_mat_hist, how='left').fillna(0)
                df_p['Perc'] = (df_p['Feito'] / df_p['Total']) * 100
                df_p['Resto'] = 100 - df_p['Perc']
                df_p = df_p.sort_values('Perc', ascending=True)

                fig_p = go.Figure()
                fig_p.add_trace(go.Bar(
                    y=df_p['materia_q'], x=df_p['Perc'], orientation='h', 
                    marker_color='#28a745', name='Concluído',
                    text=df_p['Perc'].apply(lambda x: f"<b>{x:.1f}%</b>"), textposition='inside'
                ))
                fig_p.add_trace(go.Bar(
                    y=df_p['materia_q'], x=df_p['Resto'], orientation='h', 
                    marker_color='#e9ecef', name='Pendente', hoverinfo='none'
                ))
                
                fig_p.update_layout(
                    barmode='stack', showlegend=False, height=max(400, len(df_p)*40),
                    xaxis=dict(range=[0, 100], dtick=10, title="Conclusão (%)"),
                    yaxis=dict(title=""), template="plotly_white", margin=dict(l=200)
                )
                st.plotly_chart(fig_p, use_container_width=True)

            st.subheader("📈 Constância de Estudos Diários")
            col_data = next((c for c in meu_h.columns if 'data' in c.lower()), meu_h.columns[5])
            
            meu_h['Data_Limpa'] = pd.to_datetime(meu_h[col_data].astype(str).str.strip().str[:10], format='%d/%m/%Y', errors='coerce')
            df_t = meu_h.dropna(subset=['Data_Limpa']).groupby('Data_Limpa').size().reset_index(name='Volume')
            df_t = df_t.sort_values('Data_Limpa')
            df_t['Dia_Mes'] = df_t['Data_Limpa'].dt.strftime('%d/%m/%Y')
            
            fig_t = px.area(df_t, x='Dia_Mes', y='Volume', markers=True)
            fig_t.update_traces(line_color='#1e3a8a', fillcolor='rgba(30, 58, 138, 0.2)')
            fig_t.update_layout(xaxis=dict(title="Dia da Missão", type='category'), yaxis_title="Qtd Questões", template="plotly_white")
            st.plotly_chart(fig_t, use_container_width=True)

            st.divider()
            st.subheader("🧹 Limpeza de Prontuário")
            mat_disponiveis = df_p['materia_q'].unique() if 'df_p' in locals() else meu_h[col_mat_hist].unique()
            m_reset = st.selectbox("Selecione a matéria para zerar o progresso:", mat_disponiveis)
            if st.button("ZERAR HISTÓRICO DA MATÉRIA", type="primary"): 
                reset_materia(st.session_state.usuario, m_reset)

    else:
        st.info("Nenhum dado de progresso localizado no banco.")
