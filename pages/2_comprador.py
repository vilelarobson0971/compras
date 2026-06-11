import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import numpy as np

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
    """Carrega todos os pedidos da planilha com tratamento robusto de erros"""
    try:
        # Obter todos os dados da planilha
        todos_dados = ws.get_all_values()
        
        if not todos_dados or len(todos_dados) <= 1:
            return pd.DataFrame()
        
        # Primeira linha é o cabeçalho
        cabecalho = todos_dados[0]
        
        # Limpar cabeçalho (remover espaços e caracteres especiais)
        cabecalho_limpo = []
        for col in cabecalho:
            col_limpo = col.strip().replace('_', ' ').replace('-', ' ')
            if col_limpo:
                cabecalho_limpo.append(col_limpo)
        
        # Dados a partir da segunda linha
        dados_linhas = todos_dados[1:]
        
        # Criar lista de dicionários
        registros = []
        for linha in dados_linhas:
            # Pular linhas vazias
            if not linha or all(cell == '' or cell is None for cell in linha):
                continue
            
            registro = {}
            for i, col_nome in enumerate(cabecalho_limpo):
                if i < len(linha):
                    valor = linha[i] if linha[i] else ''
                    registro[col_nome] = valor
                else:
                    registro[col_nome] = ''
            
            if registro:
                registros.append(registro)
        
        if not registros:
            return pd.DataFrame()
        
        # Converter para DataFrame
        df = pd.DataFrame(registros)
        
        # Mapeamento inteligente de colunas
        mapeamento = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'id' in col_lower:
                mapeamento[col] = 'ID'
            elif 'data' in col_lower:
                mapeamento[col] = 'Data'
            elif 'descrição' in col_lower or 'descricao' in col_lower or 'material' in col_lower:
                mapeamento[col] = 'Descrição'
            elif 'quantidade' in col_lower or 'qtd' in col_lower:
                mapeamento[col] = 'Quantidade'
            elif 'solicitante' in col_lower:
                mapeamento[col] = 'Solicitante'
            elif 'local' in col_lower:
                mapeamento[col] = 'Local'
            elif 'observação' in col_lower or 'observacao' in col_lower or 'obs' in col_lower:
                mapeamento[col] = 'Observações'
            elif 'status' in col_lower:
                mapeamento[col] = 'Status'
            elif 'ultima_atualizacao' in col_lower or 'última atualização' in col_lower or 'atualizacao' in col_lower:
                mapeamento[col] = 'Ultima_Atualizacao'
        
        # Renomear colunas
        if mapeamento:
            df = df.rename(columns=mapeamento)
        
        # Garantir que ID seja numérico
        if 'ID' in df.columns:
            df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
            df = df.dropna(subset=['ID'])
            df['ID'] = df['ID'].astype(int)
        else:
            # Criar IDs sequenciais se não existir coluna ID
            df['ID'] = range(1, len(df) + 1)
        
        # Garantir que Quantidade seja numérica
        if 'Quantidade' in df.columns:
            df['Quantidade'] = pd.to_numeric(df['Quantidade'], errors='coerce').fillna(1).astype(int)
        else:
            df['Quantidade'] = 1
        
        # Garantir que as colunas necessárias existam
        colunas_esperadas = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao']
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = 'Não informado'
        
        # Converter Data para datetime se possível
        if 'Data' in df.columns:
            try:
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
                # Substituir NaT por string
                df['Data'] = df['Data'].fillna(pd.Timestamp.now())
            except:
                pass
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro detalhado ao carregar pedidos: {str(e)}")
        st.write("Debug - Primeiras 5 linhas da planilha:")
        try:
            dados_raw = ws.get_all_values()
            st.write(dados_raw[:5])
        except:
            pass
        return pd.DataFrame()

def atualizar_status(ws, id_pedido, novo_status):
    """Atualiza o status de um pedido"""
    try:
        # Encontrar a linha do pedido (procurar na primeira coluna)
        celula = None
        dados = ws.get_all_values()
        
        for i, linha in enumerate(dados, start=1):
            if linha and len(linha) > 0 and str(linha[0]).strip() == str(id_pedido):
                celula = type('obj', (object,), {'row': i})()
                break
        
        if celula:
            cabecalho = ws.row_values(1)
            
            # Mapear colunas independente do nome
            col_status = None
            col_atualizacao = None
            
            for i, col in enumerate(cabecalho):
                col_lower = col.lower().strip()
                if 'status' in col_lower:
                    col_status = i + 1
                if 'atualizacao' in col_lower or 'atualização' in col_lower:
                    col_atualizacao = i + 1
            
            # Se não encontrou, usar posições padrão
            if not col_status:
                col_status = 8
            if not col_atualizacao:
                col_atualizacao = 9
            
            if col_status and col_atualizacao:
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
    solicitantes = ['Todos'] + sorted(df['Solicitante'].unique().tolist())
    solicitante_selecionado = st.selectbox(
        "👤 Solicitante",
        options=solicitantes,
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
    
    # Mostrar total de pedidos
    st.markdown("### 📊 Status da busca")
    st.info(f"**Total na planilha:** {len(df)} pedidos")
    
    # Botão para recarregar
    if st.button("🔄 Recarregar dados", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

# Aplicar filtros
df_filtrado = df.copy()

# Lista para mostrar quais filtros foram aplicados
filtros_aplicados = []

# Filtro de Status
if status_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_selecionados)]
    filtros_aplicados.append(f"Status: {', '.join(status_selecionados)}")

# Filtro de Solicitante
if solicitante_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Solicitante'] == solicitante_selecionado]
    filtros_aplicados.append(f"Solicitante: {solicitante_selecionado}")

# Filtro de Data (ignora hora)
if data_inicio or data_fim:
    if 'Data' in df_filtrado.columns:
        # Converter para datetime se for string
        if df_filtrado['Data'].dtype == 'object':
            df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'], errors='coerce')
        
        # Extrair apenas a data
        df_filtrado['Data_Somente'] = df_filtrado['Data'].dt.date
        
        if data_inicio:
            df_filtrado = df_filtrado[df_filtrado['Data_Somente'] >= data_inicio]
            filtros_aplicados.append(f"Data ≥ {data_inicio}")
        
        if data_fim:
            df_filtrado = df_filtrado[df_filtrado['Data_Somente'] <= data_fim]
            filtros_aplicados.append(f"Data ≤ {data_fim}")
        
        # Remover coluna auxiliar se existir
        if 'Data_Somente' in df_filtrado.columns:
            df_filtrado = df_filtrado.drop(columns=['Data_Somente'])

# Mostrar resumo dos filtros na barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Filtros aplicados:")

if filtros_aplicados:
    for filtro in filtros_aplicados:
        st.sidebar.markdown(f"- {filtro}")
    st.sidebar.markdown(f"**Resultado:** {len(df_filtrado)} pedido(s)")
    
    if len(df_filtrado) == 0 and len(df) > 0:
        st.sidebar.warning("""
        ⚠️ **Nenhum pedido encontrado!**
        
        **Sugestões:**
        • Remova alguns filtros
        • Verifique se o nome do solicitante está correto
        • Expanda o período de datas
        """)
else:
    st.sidebar.info("📌 Nenhum filtro aplicado - mostrando todos os pedidos")

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
                        st.success(f"✅ Pedido #{row['ID']} atualizado para Aguardando!")
                        st.rerun()
            
            with col2:
                if st.button("🟡 Comprando", key=f"comp_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Comprando'):
                        st.success(f"✅ Pedido #{row['ID']} atualizado para Comprando!")
                        st.rerun()
            
            with col3:
                if st.button("✅ Entregue", key=f"ent_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Entregue'):
                        st.success(f"✅ Pedido #{row['ID']} atualizado para Entregue!")
                        st.rerun()
            
            with col4:
                if st.button("❌ Cancelado", key=f"can_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Cancelado'):
                        st.warning(f"⚠️ Pedido #{row['ID']} cancelado")
                        st.rerun()
            
            with col5:
                with st.expander(f"📋 Ver detalhes completos", key=f"exp_{row['ID']}"):
                    st.json({
                        "ID": int(row['ID']),
                        "Data": str(row['Data']),
                        "Material": str(row['Descrição']),
                        "Quantidade": int(row['Quantidade']),
                        "Solicitante": str(row['Solicitante']),
                        "Local": str(row['Local']),
                        "Observações": str(row.get('Observações', '-')),
                        "Status": str(row['Status']),
                        "Última Atualização": str(row.get('Ultima_Atualizacao', '-'))
                    })
            
            st.markdown("---")
    
    # Informação de quantidade de pedidos
    st.caption(f"📊 Mostrando {len(df_filtrado)} pedido(s) de um total de {len(df)}")
    
    # Dica para muitos pedidos
    if len(df_filtrado) > 20:
        st.info("💡 **Dica:** Use os filtros na barra lateral para refinar a busca e encontrar pedidos específicos mais rapidamente.")
