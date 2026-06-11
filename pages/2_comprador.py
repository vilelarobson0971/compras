import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# Configurações
SENHA = "brasa@2026"

# Configuração da página
st.set_page_config(page_title="Gerenciar Pedidos", page_icon="📋", layout="wide")

# Função para conectar ao Google Sheets
def conectar_google_sheets():
    try:
        segredos = st.secrets["gcp_service_account"]
        
        if isinstance(segredos, str):
            creds_dict = json.loads(segredos)
        else:
            creds_dict = dict(segredos)
        
        if 'private_key' in creds_dict:
            private_key = creds_dict["private_key"]
            if isinstance(private_key, str):
                private_key = private_key.replace('\\n', '\n')
                creds_dict["private_key"] = private_key
        
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Nome correto da planilha
        sheet = client.open("Pedido_Compras")
        
        # Retornar a worksheet "Pedidos"
        return sheet.worksheet("Pedidos")
    
    except gspread.SpreadsheetNotFound:
        st.error("""
        ❌ Planilha 'Pedido_Compras' não encontrada!
        
        Verifique se:
        1. O nome exato da planilha é 'Pedido_Compras'
        2. Ela foi compartilhada com o email: bot-planilha@infralinkcompras.iam.gserviceaccount.com
        3. A permissão é de 'Editor'
        """)
        return None
    
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {str(e)}")
        return None

def carregar_pedidos(ws):
    """Carrega todos os pedidos da planilha"""
    try:
        dados = ws.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            # Garantir que ID seja numérico
            if 'ID' in df.columns:
                df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
                df = df.dropna(subset=['ID'])
                df['ID'] = df['ID'].astype(int)
            
            # Garantir que as colunas necessárias existam
            colunas_esperadas = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao']
            for col in colunas_esperadas:
                if col not in df.columns:
                    df[col] = 'Não informado'
            
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro ao carregar pedidos: {str(e)}")
        return pd.DataFrame()

def atualizar_status(ws, id_pedido, novo_status):
    """Atualiza o status de um pedido"""
    try:
        # Encontrar a linha do pedido
        celula = ws.find(str(id_pedido), in_column=1)
        if celula:
            # Colunas baseadas no cabeçalho (mais robusto)
            cabecalho = ws.row_values(1)
            
            # Encontrar índices das colunas
            try:
                col_status = cabecalho.index('Status') + 1
                col_atualizacao = cabecalho.index('Ultima_Atualizacao') + 1
            except ValueError:
                # Fallback para posições fixas
                col_status = 8  # Agora Status é a coluna 8
                col_atualizacao = 9  # Ultima_Atualizacao é a coluna 9
            
            # Atualizar células
            ws.update_cell(celula.row, col_status, novo_status)
            ws.update_cell(celula.row, col_atualizacao, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True
        return False
    except Exception as e:
        st.error(f"❌ Erro ao atualizar status: {str(e)}")
        return False

# Controle de autenticação
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.pedidos_atualizados = False

# Tela de login
if not st.session_state.logado:
    st.title("🔒 Área Restrita")
    st.markdown("### Acesso do Comprador")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        senha = st.text_input("Digite a senha:", type="password", key="senha_login")
        if st.button("🔓 Entrar", use_container_width=True):
            if senha == SENHA:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta! Tente novamente.")
    st.stop()

# Dashboard principal
st.title("📋 Gerenciamento de Pedidos")

# Conectar e carregar dados
ws = conectar_google_sheets()
if ws is None:
    st.stop()

df = carregar_pedidos(ws)

if df.empty:
    st.info("📭 Nenhum pedido encontrado na planilha.")
    st.stop()

# Sidebar com filtros
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Filtro por status
    status_options = ['Aguardando', 'Comprando', 'Entregue', 'Cancelado']
    status_selecionados = st.multiselect(
        "Status", 
        status_options,
        default=['Aguardando', 'Comprando']
    )
    
    # Filtro por solicitante
    solicitantes = df['Solicitante'].unique()
    solicitante_selecionado = st.selectbox(
        "👤 Solicitante",
        options=['Todos'] + sorted(solicitantes.tolist()),
        index=0
    )
    
    # Filtro por período
    st.subheader("📅 Período")
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data inicial", value=None)
    with col2:
        data_fim = st.date_input("Data final", value=None)
    
    st.divider()
    
    # Botão para recarregar
    if st.button("🔄 Recarregar dados", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

# Aplicar filtros
df_filtrado = df.copy()

if status_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_selecionados)]

if solicitante_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Solicitante'] == solicitante_selecionado]

if data_inicio and 'Data' in df_filtrado.columns:
    df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'])
    df_filtrado = df_filtrado[df_filtrado['Data'] >= pd.to_datetime(data_inicio)]

if data_fim and 'Data' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Data'] <= pd.to_datetime(data_fim)]

# Estatísticas
st.markdown("### 📊 Resumo")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total de Pedidos", len(df_filtrado))
with col2:
    st.metric("Aguardando", len(df_filtrado[df_filtrado['Status'] == 'Aguardando']))
with col3:
    st.metric("Comprando", len(df_filtrado[df_filtrado['Status'] == 'Comprando']))
with col4:
    st.metric("Entregues", len(df_filtrado[df_filtrado['Status'] == 'Entregue']))
with col5:
    st.metric("Cancelados", len(df_filtrado[df_filtrado['Status'] == 'Cancelado']))

# Exibir pedidos
st.markdown("### 📦 Lista de Pedidos")

if df_filtrado.empty:
    st.info("Nenhum pedido encontrado com os filtros selecionados.")
else:
    # Ordenar por ID decrescente
    df_filtrado = df_filtrado.sort_values('ID', ascending=False)
    
    # Exibir cada pedido em um card
    for idx, row in df_filtrado.iterrows():
        # Definir cor baseada no status
        cores = {
            'Aguardando': '#FFF3E0',
            'Comprando': '#FFF9C4',
            'Entregue': '#C8E6C9',
            'Cancelado': '#FFCDD2'
        }
        cor_fundo = cores.get(row['Status'], '#F5F5F5')
        
        # Card do pedido
        with st.container():
            st.markdown(f"""
            <div style='
                background-color: {cor_fundo};
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
                border-left: 5px solid #2196F3;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            '>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin: 0;'>📦 Pedido #{int(row['ID'])}</h3>
                    <span style='
                        background-color: #2196F3;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: bold;
                    '>{row['Status']}</span>
                </div>
                <hr style='margin: 10px 0;'>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
                    <div>
                        <p><strong>📝 Material:</strong> {row['Descrição']}</p>
                        <p><strong>🔢 Quantidade:</strong> {row['Quantidade']}</p>
                        <p><strong>👤 Solicitante:</strong> {row['Solicitante']}</p>
                    </div>
                    <div>
                        <p><strong>📍 Local:</strong> {row['Local']}</p>
                        <p><strong>📅 Data:</strong> {row['Data']}</p>
                        <p><strong>📝 Observações:</strong> {row.get('Observações', '-')}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botões de ação
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("⏳ Aguardando", key=f"ag_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Aguardando'):
                        st.success(f"✅ Pedido #{row['ID']} atualizado!")
                        st.rerun()
            
            with col2:
                if st.button("🟡 Comprando", key=f"comp_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Comprando'):
                        st.success(f"✅ Pedido #{row['ID']} atualizado!")
                        st.rerun()
            
            with col3:
                if st.button("✅ Entregue", key=f"ent_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Entregue'):
                        st.success(f"✅ Pedido #{row['ID']} atualizado!")
                        st.rerun()
            
            with col4:
                if st.button("❌ Cancelado", key=f"can_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Cancelado'):
                        st.warning(f"⚠️ Pedido #{row['ID']} cancelado")
                        st.rerun()
            
            with col5:
                # Botão para ver detalhes completos
                with st.expander(f"📋 Ver detalhes completos", key=f"exp_{row['ID']}"):
                    st.json({
                        "ID": int(row['ID']),
                        "Data": row['Data'],
                        "Material": row['Descrição'],
                        "Quantidade": row['Quantidade'],
                        "Solicitante": row['Solicitante'],
                        "Local": row['Local'],
                        "Observações": row.get('Observações', '-'),
                        "Status": row['Status'],
                        "Última Atualização": row.get('Ultima_Atualizacao', '-')
                    })
            
            st.markdown("---")
    
    # Informação de quantidade
    st.caption(f"📊 Mostrando {len(df_filtrado)} pedido(s) de um total de {len(df)}")
    
    # Paginação para muitos pedidos
    if len(df_filtrado) > 20:
        st.info(f"💡 Dica: Use os filtros na barra lateral para refinar a busca e encontrar pedidos específicos mais rapidamente.")
