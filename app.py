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
    /* Botão WhatsApp */
    .btn-whatsapp {
        display: block; width: 100%; background-color: #25D366; color: white !important;
        text-align: center; padding: 12px; border-radius: 8px; text-decoration: none;
        font-weight: bold; margin-top: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: 0.3s;
    }
    .btn-whatsapp:hover { background-color: #128C7E; }
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

# --- FUNÇÕES DE BANCO E CALLBACKS ---
def registrar_log(aba, dados):
    try:
        # Puxa versão fresquinha silenciosamente e salva
        df_atual = conn.read(spreadsheet=MINHA_URL, worksheet=aba, ttl=0)
        df_novo = pd.concat([df_atual, pd.DataFrame([dados])], ignore_index=True)
        conn.update(spreadsheet=MINHA_URL, worksheet=aba, data=df_novo)
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# CALLBACK: Executa instantaneamente sem quebrar a posição da tela
def validar_questao_callback(q_id, radio_key, ops, gabarito, explicacao, pegadinha, materia, topico, usuario):
    escolha = st.session_state[radio_key]
    letra = [l for l, t in ops.items() if t == escolha][0]
    status = "Acerto" if letra == str(gabarito).strip().upper() else "Erro"
    
    # 1. Salva no banco de dados
    registrar_log("Log_Progresso", {
        "Usuario": usuario, "Materia": materia, 
        "Titulo": topico, "Questao": q_id, 
        "Status": status, "Data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    
    # 2. Salva na memória da sessão para feedback instantâneo na UI
    st.session_state[f"status_q_{q_id}"] = status
    st.session_state[f"gab_q_{q_id}"] = gabarito
    st.session_state[f"exp_q_{q_id}"] = explicacao
    st.session_state[f"pega_q_{q_id}"] = pegadinha

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

# --- LOGIN COM WHATSAPP E TESTE GRÁTIS ---
if not st.session_state.autenticado:
    st.markdown('<div style="text-align:center; padding-top: 50px;">', unsafe_allow_html=True)
    st.image(URL_BRASAO, width=120)
    st.title("ESTRATÉGIA GABARITO")
    st.markdown("### 🎯 EAP 3º Sgt PM 2026")
    
    col_vazia1, col_form, col_vazia2 = st.columns([1, 1.5, 1])
    
    with col_form:
        with st.form("login"):
            u_input = st.text_input("Usuário ou E-mail:").strip().lower()
            p_input = st.text_input("Senha:", type="password").strip()
            submit = st.form_submit_button("INICIAR MISSÃO", use_container_width=True)
            
            if submit:
                df_u = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Usuarios", ttl="10m"))
                if not df_u.empty:
                    col_usu = next((c for c in df_u.columns if 'usuario' in c.lower()), df_u.columns[0])
                    col_sen = next((c for c in df_u.columns if 'senha' in c.lower()), df_u.columns[1])
                    col_val = next((c for c in df_u.columns if 'validade' in c.lower() or 'expiracao' in c.lower()), None)
                    
                    user_row = df_u[df_u[col_usu].str.lower() == u_input]
                    
                    if not user_row.empty and str(user_row.iloc[0][col_sen]) == p_input:
                        acesso_liberado = True
                        if col_val is not None:
                            data_limite_str = str(user_row.iloc[0][col_val]).strip()
                            if data_limite_str and data_limite_str.lower() not in ['nan', 'none', '']:
                                try:
                                    data_limite = datetime.datetime.strptime(data_limite_str, "%d/%m/%Y").date()
                                    if datetime.date.today() > data_limite:
                                        acesso_liberado = False
                                except ValueError:
                                    pass 
                        
                        if acesso_liberado:
                            st.session_state.autenticado = True
                            st.session_state.usuario = u_input
                            st.rerun()
                        else:
                            st.error("⏳ SEU TESTE GRÁTIS EXPIROU!")
                            st.warning("O seu tempo de missão acabou. O QG de Inteligência está bloqueado. Adquira o acesso definitivo e continue sua preparação para o EAP 2026!")
                    else: 
                        st.error("❌ Acesso Negado. Verifique os dados inseridos.")

        # --- BOTÃO DO WHATSAPP ---
        NUMERO_WHATSAPP = "5535999999999"  # <--- COLOCAR SEU NÚMERO AQUI
        MENSAGEM_WHATSAPP = "Olá! Tenho interesse em adquirir o acesso definitivo ao aplicativo Questões EAP 3º Sgt PM 2026."
        url_whatsapp = f"https://wa.me/{NUMERO_WHATSAPP}?text={MENSAGEM_WHATSAPP.replace(' ', '%20')}"
        
        st.markdown(f"""
            <a href="{url_whatsapp}" target="_blank" class="btn-whatsapp">
                <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="22" style="vertical-align: middle; margin-right: 8px;">
                Adquira seu Acesso / Suporte
            </a>
        """, unsafe_allow_html=True)
        
    st.stop()

# --- CARREGA HISTÓRICOS ---
df_hist_q = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Log_Progresso", ttl="10m"))
df_hist_a = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet="Assuntos_Estudados", ttl="10m"))

# --- NAVEGAÇÃO ---
st.sidebar.image(URL_BRASAO, width=80)
st.sidebar.markdown(f"### 🎖️ Combatente: {st.session_state.usuario.split('@')[0].upper()}")
menu = st.sidebar.radio("Quartel General:", ["📝 Simulado", "📊 Performance", "🚪 Sair"])

if menu == "🚪 Sair":
    st.session_state.autenticado = False
    st.rerun()

# --- SIMULADO (INSTANTÂNEO) ---
if menu == "📝 Simulado":
    area = st.sidebar.selectbox("Área do Edital:", ["Legislacao_Institucional", "Doutrina_Operacional", "Legislacao_Juridica"])
    try:
        df_q = limpar_dados(conn.read(spreadsheet=MINHA_URL, worksheet=area, ttl="10m"))
        if not df_q.empty:
            while df_q.shape[1] < 13:
                df_q[f"coluna_{df_q.shape[1]}"] = ""

            col_id = df_q.columns[0]; col_pergunta = df_q.columns[3]; col_gab = df_q.columns[8]
            col_exp = df_q.columns[9]; col_pega = df_q.columns[10]
            col_mat = df_q.columns[11]; col_topico = df_q.columns[12]
            
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
                        registrar_log("Assuntos_Estudados", {"Usuario": st.session_state.usuario, "Materia": sel_lei, "Topico": id_a, "Status": "Concluído", "Data": datetime.datetime.now().strftime("%d/%m/%Y")})
                        st.cache_data.clear() # Limpa cache para o botão sumir
                        st.rerun()
            st.divider()

            df_exibir = df_f_lei if sel_titulo == "VER TUDO" else df_f_lei[df_f_lei[col_topico] == sel_titulo]

            # Lista de resolvidas no Banco
            minhas_q_banco = []
            if not df_hist_q.empty:
                col_usu_hist = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
                col_q_hist = next((c for c in df_hist_q.columns if 'questao' in c.lower()), df_hist_q.columns[3])
                minhas_q_banco = df_hist_q[df_hist_q[col_usu_hist].str.lower() == st.session_state.usuario][col_q_hist].tolist()

            for i, row in df_exibir.iterrows():
                q_id = str(row[col_id])
                
                # Inteligência de Estado: Verifica se foi feita no banco OU agorinha na memória
                feita_banco = q_id in minhas_q_banco
                feita_agora = f"status_q_{q_id}" in st.session_state
                ja_resolvida = feita_banco or feita_agora
                
                badge = '<span class="status-badge concluido">RESOLVIDA</span>' if ja_resolvida else '<span class="status-badge pendente">PENDENTE</span>'
                
                with st.container():
                    st.markdown(f'<div class="question-box"><b>Q{q_id}</b> {badge}<br><br>{row[col_pergunta]}</div>', unsafe_allow_html=True)
                    ops = {"A": row.iloc[4], "B": row.iloc[5], "C": row.iloc[6], "D": row.iloc[7]}
                    opcoes_validas = [v for v in ops.values() if str(v).lower() != 'nan' and str(v).strip() != '']
                    
                    # Radio bloqueado se já foi resolvida
                    escolha = st.radio(f"Res Q{q_id}:", opcoes_validas, key=f"r_{q_id}", label_visibility="collapsed", disabled=ja_resolvida)
                    
                    if not ja_resolvida:
                        topico_log = row[col_topico] if sel_titulo == "VER TUDO" else sel_titulo
                        st.button(f"Validar Q{q_id}", key=f"b_{q_id}", use_container_width=True, 
                                  on_click=validar_questao_callback, 
                                  args=(q_id, f"r_{q_id}", ops, row[col_gab], row[col_exp], row[col_pega], sel_lei, topico_log, st.session_state.usuario))
                    else:
                        # Exibe o Feedback
                        if feita_agora:
                            status = st.session_state[f"status_q_{q_id}"]
                            if status == "Acerto": st.success("🎯 ACERTOU!")
                            else: st.error(f"❌ ERROU! Gabarito: {st.session_state[f'gab_q_{q_id}']}")
                            
                            exp_texto = str(st.session_state[f"exp_q_{q_id}"]).strip()
                            if exp_texto.lower() not in ['nan', 'none', '']: st.info(f"💡 **Comentário:** {exp_texto}")
                                
                            pega_texto = str(st.session_state[f"pega_q_{q_id}"]).strip()
                            if pega_texto.lower() not in ['nan', 'none', '']: st.warning(f"🚨 **Pegadinha CRS:** {pega_texto}")
                        else:
                            st.success("✅ Questão já resolvida em treinamentos anteriores.")
                            with st.expander("Ver Gabarito e Comentários"):
                                st.write(f"**Gabarito Correto:** {row[col_gab]}")
                                exp_texto = str(row[col_exp]).strip()
                                if exp_texto.lower() not in ['nan', 'none', '']: st.info(f"💡 **Comentário:** {exp_texto}")
                                pega_texto = str(row[col_pega]).strip()
                                if pega_texto.lower() not in ['nan', 'none', '']: st.warning(f"🚨 **Pegadinha CRS:** {pega_texto}")
                                
    except Exception as e: st.error(f"Erro no Simulado: {e}")

# --- PERFORMANCE ---
elif menu == "📊 Performance":
    col_t1, col_t2 = st.columns([3, 1])
    col_t1.title("📊 Inteligência de Performance")
    
    # Botão para sincronizar dados da nuvem para o painel
    if col_t2.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    if not df_hist_q.empty:
        col_usu_hist = next((c for c in df_hist_q.columns if 'usuario' in c.lower()), df_hist_q.columns[0])
        meu_h = df_hist_q[df_hist_q[col_usu_hist].str.lower() == st.session_state.usuario].copy()
        
        if meu_h.empty:
            st.warning("Nenhum dado sincronizado. Resolva questões e clique em 'Atualizar Dados'.")
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
                fig_p.add_trace(go.Bar(y=df_p['materia_q'], x=df_p['Perc'], orientation='h', marker_color='#28a745', name='Concluído', text=df_p['Perc'].apply(lambda x: f"<b>{x:.1f}%</b>"), textposition='inside'))
                fig_p.add_trace(go.Bar(y=df_p['materia_q'], x=df_p['Resto'], orientation='h', marker_color='#e9ecef', name='Pendente', hoverinfo='none'))
                
                fig_p.update_layout(barmode='stack', showlegend=False, height=max(400, len(df_p)*40), xaxis=dict(range=[0, 100], dtick=10, title="Conclusão (%)"), yaxis=dict(title=""), template="plotly_white", margin=dict(l=200))
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
