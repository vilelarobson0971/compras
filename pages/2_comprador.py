import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import time

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
        
        sheet = client.open("Pedido_Compras")
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
    """Carrega todos os pedidos da planilha garantindo IDs únicos"""
    try:
        todos_dados = ws.get_all_values()
        
        if not todos_dados or len(todos_dados) <= 1:
            return []
        
        cabecalho = todos_dados[0]
        
        # Identificar a coluna ID (primeira coluna)
        # Garantir que estamos usando a primeira coluna como ID
        idx_id = 0  # Primeira coluna sempre será o ID
        
        # Mapear outros índices
        idx_data = 1 if len(cabecalho) > 1 else None
        idx_desc = 2 if len(cabecalho) > 2 else None
        idx_qtd = 3 if len(cabecalho) > 3 else None
        idx_solicitante = 4 if len(cabecalho) > 4 else None
        idx_local = 5 if len(cabecalho) > 5 else None
        idx_obs = 6 if len(cabecalho) > 6 else None
        idx_status = 7 if len(cabecalho) > 7 else None
        idx_atualizacao = 8 if len(cabecalho) > 8 else None
        
        # Processar linhas de dados
        pedidos = []
        for linha in todos_dados[1:]:
            if not linha or all(cell == '' or cell is None for cell in linha):
                continue
            
            # Extrair ID - garantir que é um número válido
            id_valor = linha[idx_id] if idx_id is not None and idx_id < len(linha) else ''
            
            # Tentar converter ID para inteiro
            try:
                id_int = int(float(str(id_valor).strip())) if id_valor else 0
            except:
                id_int = 0
            
            if id_int == 0:
                # Se ID for inválido, pular este registro
                continue
            
            pedido = {
                'ID': id_int,
                'Data': linha[idx_data] if idx_data is not None and idx_data < len(linha) else '',
                'Descrição': linha[idx_desc] if idx_desc is not None and idx_desc < len(linha) else '',
                'Quantidade': linha[idx_qtd] if idx_qtd is not None and idx_qtd < len(linha) else '1',
                'Solicitante': linha[idx_solicitante] if idx_solicitante is not None and idx_solicitante < len(linha) else '',
                'Local': linha[idx_local] if idx_local is not None and idx_local < len(linha) else '',
                'Observações': linha[idx_obs] if idx_obs is not None and idx_obs < len(linha) else '',
                'Status': linha[idx_status] if idx_status is not None and idx_status < len(linha) else 'Aguardando',
                'Ultima_Atualizacao': linha[idx_atualizacao] if idx_atualizacao is not None and idx_atualizacao < len(linha) else ''
            }
            
            # Validar dados mínimos
            if pedido['Descrição'] and pedido['ID'] > 0:
                pedidos.append(pedido)
        
        # Ordenar por ID
        pedidos.sort(key=lambda x: x['ID'])
        
        return pedidos
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar pedidos: {str(e)}")
        return []

def atualizar_status(ws, id_pedido, novo_status):
    """Atualiza o status de um pedido"""
    try:
        todas_linhas = ws.get_all_values()
        
        linha_encontrada = None
        for i, linha in enumerate(todas_linhas, start=1):
            if linha and len(linha) > 0:
                # Comparar como string para garantir
                id_linha = str(linha[0]).strip()
                id_busca = str(id_pedido).strip()
                if id_linha == id_busca:
                    linha_encontrada = i
                    break
        
        if linha_encontrada:
            cabecalho = todas_linhas[0]
            col_status = None
            col_atualizacao = None
            
            for i, col in enumerate(cabecalho, start=1):
                col_lower = col.lower().strip()
                if 'status' in col_lower:
                    col_status = i
                if 'atualizacao' in col_lower or 'atualização' in col_lower:
                    col_atualizacao = i
            
            if not col_status:
                col_status = 8
            if not col_atualizacao:
                col_atualizacao = 9
            
            ws.update_cell(linha_encontrada, col_status, novo_status)
            ws.update_cell(linha_encontrada, col_atualizacao, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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

# Carregar pedidos
pedidos_lista = carregar_pedidos(ws)

if not pedidos_lista:
    st.info("📭 Nenhum pedido encontrado na planilha.")
    st.stop()

# Converter para DataFrame
df = pd.DataFrame(pedidos_lista)

# Verificar se temos IDs únicos
st.sidebar.write(f"**IDs encontrados:** {sorted(df['ID'].unique())}")

# Sidebar com filtros
with st.sidebar:
    st.header("🔍 Filtros")
    
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
    
    # Filtro por ID
    ids_disponiveis = ['Todos'] + sorted([str(id) for id in df['ID'].unique()])
    id_selecionado = st.selectbox(
        "🔢 Número do Pedido",
        options=ids_disponiveis,
        index=0
    )
    
    st.subheader("📅 Período")
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data inicial", value=None)
    with col2:
        data_fim = st.date_input("Data final", value=None)
    
    st.divider()
    
    st.markdown("### 📊 Status da busca")
    st.info(f"**Total na planilha:** {len(df)} pedidos")
    
    if st.button("🔄 Recarregar dados", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

# Aplicar filtros
df_filtrado = df.copy()
filtros_aplicados = []

if status_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_selecionados)]
    filtros_aplicados.append(f"Status: {', '.join(status_selecionados)}")

if solicitante_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Solicitante'] == solicitante_selecionado]
    filtros_aplicados.append(f"Solicitante: {solicitante_selecionado}")

if id_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['ID'] == int(id_selecionado)]
    filtros_aplicados.append(f"ID: {id_selecionado}")

if data_inicio or data_fim:
    if 'Data' in df_filtrado.columns:
        df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'], errors='coerce')
        df_filtrado['Data_Somente'] = df_filtrado['Data'].dt.date
        
        if data_inicio:
            df_filtrado = df_filtrado[df_filtrado['Data_Somente'] >= data_inicio]
            filtros_aplicados.append(f"Data ≥ {data_inicio}")
        
        if data_fim:
            df_filtrado = df_filtrado[df_filtrado['Data_Somente'] <= data_fim]
            filtros_aplicados.append(f"Data ≤ {data_fim}")
        
        if 'Data_Somente' in df_filtrado.columns:
            df_filtrado = df_filtrado.drop(columns=['Data_Somente'])

# Mostrar resumo dos filtros
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
    df_filtrado = df_filtrado.sort_values('ID', ascending=False)
    
    # Exibir cada pedido em um card
    for idx, row in df_filtrado.iterrows():
        pedido_id = int(row['ID'])
        
        cores = {
            'Aguardando': '#FFF3E0',
            'Comprando': '#FFF9C4',
            'Entregue': '#C8E6C9',
            'Cancelado': '#FFCDD2'
        }
        cor_fundo = cores.get(row['Status'], '#F5F5F5')
        
        data_exibicao = row['Data']
        if pd.notna(data_exibicao):
            if isinstance(data_exibicao, pd.Timestamp):
                data_exibicao = data_exibicao.strftime('%d/%m/%Y %H:%M')
        
        # Garantir que quantidade seja número
        try:
            quantidade = int(row['Quantidade'])
        except:
            quantidade = row['Quantidade']
        
        # Gerar chave única para os botões
        unique_key = f"{pedido_id}_{idx}_{int(time.time() * 1000)}"
        
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
                    <h3 style='margin: 0;'>📦 Pedido #{pedido_id}</h3>
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
                        <p><strong>🔢 Quantidade:</strong> {quantidade}</p>
                        <p><strong>👤 Solicitante:</strong> {row['Solicitante']}</p>
                    </div>
                    <div>
                        <p><strong>📍 Local:</strong> {row['Local']}</p>
                        <p><strong>📅 Data:</strong> {data_exibicao}</p>
                        <p><strong>📝 Observações:</strong> {row.get('Observações', '-')}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botões de ação
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("⏳ Aguardando", key=f"ag_{unique_key}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Aguardando'):
                        st.success(f"✅ Pedido #{pedido_id} atualizado para Aguardando!")
                        time.sleep(0.5)
                        st.rerun()
            
            with col2:
                if st.button("🟡 Comprando", key=f"comp_{unique_key}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Comprando'):
                        st.success(f"✅ Pedido #{pedido_id} atualizado para Comprando!")
                        time.sleep(0.5)
                        st.rerun()
            
            with col3:
                if st.button("✅ Entregue", key=f"ent_{unique_key}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Entregue'):
                        st.success(f"✅ Pedido #{pedido_id} atualizado para Entregue!")
                        time.sleep(0.5)
                        st.rerun()
            
            with col4:
                if st.button("❌ Cancelado", key=f"can_{unique_key}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Cancelado'):
                        st.warning(f"⚠️ Pedido #{pedido_id} cancelado")
                        time.sleep(0.5)
                        st.rerun()
            
            with col5:
                with st.expander(f"📋 Ver detalhes completos", key=f"exp_{unique_key}"):
                    st.json({
                        "ID": pedido_id,
                        "Data": str(row['Data']),
                        "Material": str(row['Descrição']),
                        "Quantidade": quantidade,
                        "Solicitante": str(row['Solicitante']),
                        "Local": str(row['Local']),
                        "Observações": str(row.get('Observações', '-')),
                        "Status": str(row['Status']),
                        "Última Atualização": str(row.get('Ultima_Atualizacao', '-'))
                    })
            
            st.markdown("---")
    
    st.caption(f"📊 Mostrando {len(df_filtrado)} pedido(s) de um total de {len(df)}")
    
    if len(df_filtrado) > 20:
        st.info("💡 **Dica:** Use os filtros na barra lateral para refinar a busca e encontrar pedidos específicos mais rapidamente.")
