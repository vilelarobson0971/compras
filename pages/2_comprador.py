import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import requests
from PIL import Image
from io import BytesIO

# Configurações
SENHA = "brasa@2026"

st.set_page_config(page_title="Gerenciar Pedidos", page_icon="📋", layout="wide")

# Função para formatar data para exibição
def formatar_data_br(data_str):
    try:
        if pd.isna(data_str) or data_str == '':
            return ''
        dt = pd.to_datetime(data_str)
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return str(data_str)

# Função para carregar imagem da URL
def carregar_imagem_url(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            return img
    except:
        pass
    return None

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
    
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {str(e)}")
        return None

def carregar_pedidos(ws):
    try:
        todos_dados = ws.get_all_values()
        
        if not todos_dados or len(todos_dados) <= 1:
            return []
        
        pedidos = []
        for linha in todos_dados[1:]:
            if not linha or len(linha) < 3:
                continue
            
            try:
                id_int = int(float(str(linha[0]).strip())) if linha[0] else 0
            except:
                id_int = 0
            
            if id_int == 0:
                continue
            
            pedido = {
                'ID': id_int,
                'Data': linha[1] if len(linha) > 1 else '',
                'Descrição': linha[2] if len(linha) > 2 else '',
                'Quantidade': linha[3] if len(linha) > 3 else '1',
                'Solicitante': linha[4] if len(linha) > 4 else '',
                'Local': linha[5] if len(linha) > 5 else '',
                'Observações': linha[6] if len(linha) > 6 else '',
                'Foto_Link': linha[7] if len(linha) > 7 else '',
                'Status': linha[8] if len(linha) > 8 else 'Aguardando',
                'Ultima_Atualizacao': linha[9] if len(linha) > 9 else ''
            }
            
            if pedido['Descrição'] and pedido['ID'] > 0:
                pedidos.append(pedido)
        
        return pedidos
    except Exception as e:
        st.error(f"❌ Erro ao carregar pedidos: {str(e)}")
        return []

def atualizar_status(ws, id_pedido, novo_status):
    try:
        todas_linhas = ws.get_all_values()
        
        linha_encontrada = None
        for i, linha in enumerate(todas_linhas, start=1):
            if linha and len(linha) > 0:
                id_linha = str(linha[0]).strip()
                id_busca = str(id_pedido).strip()
                if id_linha == id_busca:
                    linha_encontrada = i
                    break
        
        if linha_encontrada:
            ws.update_cell(linha_encontrada, 9, novo_status)
            ws.update_cell(linha_encontrada, 10, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True
        else:
            st.error(f"❌ Pedido #{id_pedido} não encontrado na planilha!")
            return False
            
    except Exception as e:
        st.error(f"❌ Erro ao atualizar status: {str(e)}")
        return False

# Autenticação
if 'logado' not in st.session_state:
    st.session_state.logado = False

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

st.title("📋 Gerenciamento de Pedidos")

ws = conectar_google_sheets()
if ws is None:
    st.stop()

pedidos_lista = carregar_pedidos(ws)

if not pedidos_lista:
    st.info("📭 Nenhum pedido encontrado na planilha.")
    st.stop()

df = pd.DataFrame(pedidos_lista)

# Sidebar com filtros
with st.sidebar:
    st.header("🔍 Filtros")
    
    status_options = ['Aguardando', 'Comprando', 'Entregue', 'Cancelado']
    status_selecionados = st.multiselect(
        "Status", 
        status_options,
        default=['Aguardando', 'Comprando']
    )
    
    solicitantes = ['Todos'] + sorted(df['Solicitante'].unique().tolist())
    solicitante_selecionado = st.selectbox(
        "👤 Solicitante",
        options=solicitantes,
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
    
    # Filtro para pedidos com foto
    mostrar_com_foto = st.checkbox("📸 Mostrar apenas pedidos com foto")
    
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

if mostrar_com_foto:
    df_filtrado = df_filtrado[df_filtrado['Foto_Link'].notna() & (df_filtrado['Foto_Link'] != '')]
    filtros_aplicados.append("Apenas pedidos com foto")

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

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Filtros aplicados:")

if filtros_aplicados:
    for filtro in filtros_aplicados:
        st.sidebar.markdown(f"- {filtro}")
    st.sidebar.markdown(f"**Resultado:** {len(df_filtrado)} pedido(s)")
    
    if len(df_filtrado) == 0 and len(df) > 0:
        st.sidebar.warning("Nenhum pedido encontrado com os filtros selecionados.")
else:
    st.sidebar.info("📌 Nenhum filtro aplicado - mostrando todos os pedidos")

# Estatísticas
st.markdown("### 📊 Resumo")
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total", len(df_filtrado))
with col2:
    st.metric("Aguardando", len(df_filtrado[df_filtrado['Status'] == 'Aguardando']))
with col3:
    st.metric("Comprando", len(df_filtrado[df_filtrado['Status'] == 'Comprando']))
with col4:
    st.metric("Entregues", len(df_filtrado[df_filtrado['Status'] == 'Entregue']))
with col5:
    st.metric("Cancelados", len(df_filtrado[df_filtrado['Status'] == 'Cancelado']))
with col6:
    st.metric("📸 Com Foto", len(df_filtrado[df_filtrado['Foto_Link'].notna() & (df_filtrado['Foto_Link'] != '')]))

# Exibir pedidos
st.markdown("### 📦 Lista de Pedidos")

if df_filtrado.empty:
    st.info("Nenhum pedido encontrado com os filtros selecionados.")
else:
    df_filtrado = df_filtrado.sort_values('ID', ascending=False)
    
    for idx, row in df_filtrado.iterrows():
        pedido_id = int(row['ID'])
        
        cores = {
            'Aguardando': '#FFF3E0',
            'Comprando': '#FFF9C4',
            'Entregue': '#C8E6C9',
            'Cancelado': '#FFCDD2'
        }
        cor_fundo = cores.get(row['Status'], '#F5F5F5')
        
        data_exibicao = formatar_data_br(row['Data'])
        
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
                        <p><strong>🔢 Quantidade:</strong> {row['Quantidade']}</p>
                        <p><strong>👤 Solicitante:</strong> {row['Solicitante']}</p>
                        <p><strong>📍 Local:</strong> {row['Local']}</p>
                        <p><strong>📅 Data:</strong> {data_exibicao}</p>
                    </div>
                    <div>
                        <p><strong>📝 Observações:</strong> {row.get('Observações', '-')}</p>
            """)
            
            # Exibir foto se houver
            if row.get('Foto_Link') and row['Foto_Link'] != '':
                st.markdown(f'<p><strong>📸 Foto do Item:</strong></p>', unsafe_allow_html=True)
                img = carregar_imagem_url(row['Foto_Link'])
                if img:
                    st.image(img, use_container_width=False, width=200)
                else:
                    st.markdown(f'<a href="{row["Foto_Link"]}" target="_blank">🔗 Clique aqui para ver a foto</a>', unsafe_allow_html=True)
            else:
                st.markdown('<p><em>📸 Nenhuma foto anexada</em></p>', unsafe_allow_html=True)
            
            st.markdown(f"""
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botões de ação
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("⏳ Aguardando", key=f"btn_ag_{pedido_id}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Aguardando'):
                        st.success(f"✅ Pedido #{pedido_id} atualizado!")
                        st.rerun()
            
            with col2:
                if st.button("🟡 Comprando", key=f"btn_comp_{pedido_id}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Comprando'):
                        st.success(f"✅ Pedido #{pedido_id} atualizado!")
                        st.rerun()
            
            with col3:
                if st.button("✅ Entregue", key=f"btn_ent_{pedido_id}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Entregue'):
                        st.success(f"✅ Pedido #{pedido_id} atualizado!")
                        st.rerun()
            
            with col4:
                if st.button("❌ Cancelado", key=f"btn_can_{pedido_id}", use_container_width=True):
                    if atualizar_status(ws, pedido_id, 'Cancelado'):
                        st.warning(f"⚠️ Pedido #{pedido_id} cancelado")
                        st.rerun()
            
            st.markdown("---")
    
    st.caption(f"📊 Mostrando {len(df_filtrado)} pedido(s) de um total de {len(df)}")
