import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Configuração da página
st.set_page_config(
    page_title="Área do Comprador",
    page_icon="🔒",
    layout="wide"
)

# Senha definida
SENHA_COMPRADOR = "brasa@2026"

def init_google_sheets():
    """Inicializa a conexão com Google Sheets"""
    try:
        creds_dict = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open(st.secrets["google_sheets"]["sheet_name"])
        worksheet = sheet.worksheet("Pedidos")
        
        return worksheet
    
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {str(e)}")
        return None

def carregar_pedidos(worksheet):
    """Carrega todos os pedidos da planilha"""
    try:
        dados = worksheet.get_all_records()
        df = pd.DataFrame(dados)
        
        if not df.empty:
            # Garantir que a coluna ID existe
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar pedidos: {str(e)}")
        return pd.DataFrame()

def atualizar_status(worksheet, pedido_id, novo_status):
    """Atualiza o status de um pedido"""
    try:
        # Encontrar a linha do pedido
        celula_id = worksheet.find(str(pedido_id))
        if celula_id:
            # Status está na coluna 7 (G)
            worksheet.update_cell(celula_id.row, 7, novo_status)
            # Atualizar data do status
            worksheet.update_cell(celula_id.row, 8, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar status: {str(e)}")
        return False

# Verificar autenticação
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Área Restrita - Comprador")
    st.markdown("---")
    
    senha = st.text_input("Digite a senha de acesso:", type="password")
    
    if st.button("Acessar", use_container_width=True):
        if senha == SENHA_COMPRADOR:
            st.session_state.autenticado = True
            st.success("✅ Acesso concedido!")
            st.rerun()
        else:
            st.error("❌ Senha incorreta!")
    
    st.stop()

# Página principal do comprador
st.title("📋 Gerenciamento de Pedidos")
st.markdown("---")

# Carregar dados
worksheet = init_google_sheets()

if worksheet:
    df = carregar_pedidos(worksheet)
    
    if not df.empty:
        # Filtros
        st.subheader("🔍 Filtros")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filtro = st.multiselect(
                "Status",
                options=['Aguardando', 'Comprando', 'Entregue', 'Cancelado'],
                default=['Aguardando', 'Comprando', 'Entregue', 'Cancelado']
            )
        
        with col2:
            if 'Local Utilização' in df.columns:
                locais = df['Local Utilização'].unique().tolist()
                local_filtro = st.multiselect("Local", options=locais)
        
        with col3:
            search = st.text_input("🔎 Buscar por descrição")
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if status_filtro:
            df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_filtro)]
        
        if local_filtro and 'Local Utilização' in df.columns:
            df_filtrado = df_filtrado[df_filtrado['Local Utilização'].isin(local_filtro)]
        
        if search:
            df_filtrado = df_filtrado[df_filtrado['Descrição Material'].str.contains(search, case=False, na=False)]
        
        st.markdown("---")
        st.subheader(f"📊 Pedidos Encontrados: {len(df_filtrado)}")
        
        # Exibir pedidos com cores baseadas no status
        for idx, row in df_filtrado.iterrows():
            # Definir cor do card baseado no status
            status = row['Status']
            if status == 'Aguardando':
                bg_color = "#FFFFFF"
                border_color = "#E0E0E0"
            elif status == 'Comprando':
                bg_color = "#FFF9C4"  # Amarelo claro
                border_color = "#FDD835"
            elif status == 'Entregue':
                bg_color = "#C8E6C9"  # Verde claro
                border_color = "#4CAF50"
            elif status == 'Cancelado':
                bg_color = "#FFCDD2"  # Vermelho claro
                border_color = "#F44336"
            else:
                bg_color = "#FFFFFF"
                border_color = "#E0E0E0"
            
            # Criar card
            st.markdown(f"""
            <div style='
                background-color: {bg_color};
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid {border_color};
                margin-bottom: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            '>
                <h3 style='margin-top: 0;'>📦 Pedido #{int(row['ID'])}</h3>
                <p><strong>Descrição:</strong> {row['Descrição Material']}</p>
                <p><strong>Quantidade:</strong> {row['Quantidade']}</p>
                <p><strong>Local:</strong> {row['Local Utilização']}</p>
                <p><strong>Observações:</strong> {row['Observações'] if pd.notna(row['Observações']) else 'Nenhuma'}</p>
                <p><strong>Data do Pedido:</strong> {row['Data']}</p>
                <p><strong>Status Atual:</strong> {status}</p>
                <p><strong>Última Atualização:</strong> {row['Status_Atualizado']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Botões de ação
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"⏳ Aguardando", key=f"ag_{row['ID']}"):
                    if atualizar_status(worksheet, row['ID'], 'Aguardando'):
                        st.success(f"Pedido #{row['ID']} alterado para AGUARDANDO!")
                        st.rerun()
            
            with col2:
                if st.button(f"🟡 Comprando", key=f"comp_{row['ID']}"):
                    if atualizar_status(worksheet, row['ID'], 'Comprando'):
                        st.success(f"Pedido #{row['ID']} alterado para COMPRANDO!")
                        st.rerun()
            
            with col3:
                if st.button(f"✅ Entregue", key=f"ent_{row['ID']}"):
                    if atualizar_status(worksheet, row['ID'], 'Entregue'):
                        st.success(f"Pedido #{row['ID']} alterado para ENTREGUE!")
                        st.rerun()
            
            with col4:
                if st.button(f"❌ Cancelado", key=f"can_{row['ID']}"):
                    if atualizar_status(worksheet, row['ID'], 'Cancelado'):
                        st.warning(f"Pedido #{row['ID']} CANCELADO!")
                        st.rerun()
            
            st.markdown("---")
        
        # Botão de logout
        if st.button("🚪 Sair da Área do Comprador", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
    
    else:
        st.info("📭 Nenhum pedido encontrado no sistema.")
else:
    st.error("❌ Não foi possível conectar ao banco de dados.")