import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Sistema de Pedidos", page_icon="🛒", layout="wide")

SENHA_COMPRADOR = "brasa@2026"

# Conectar ao Google Sheets
def conectar_google_sheets():
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
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Pedidos_Compras")
    
    try:
        worksheet = sheet.worksheet("Pedidos")
    except:
        worksheet = sheet.add_worksheet("Pedidos", 1000, 20)
        worksheet.append_row(['ID', 'Data', 'Descrição', 'Quantidade', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao'])
    
    return worksheet

def salvar_pedido(ws, desc, qtd, local, obs):
    dados = ws.get_all_values()
    novo_id = len(dados)
    
    linha = [
        novo_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        desc, qtd, local, obs,
        'Aguardando',
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    ws.append_row(linha)
    return novo_id

def carregar_pedidos(ws):
    dados = ws.get_all_records()
    return pd.DataFrame(dados)

def atualizar_status(ws, id_pedido, novo_status):
    celula = ws.find(str(id_pedido))
    if celula:
        ws.update_cell(celula.row, 7, novo_status)
        ws.update_cell(celula.row, 8, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return True
    return False

# Menu de navegação
st.sidebar.title("📋 Menu")
st.sidebar.markdown("---")
opcao = st.sidebar.radio(
    "Escolha uma opção:",
    ["📝 Fazer Pedido", "🔒 Área do Comprador"]
)

# Página de Fazer Pedido
if opcao == "📝 Fazer Pedido":
    st.title("📝 Novo Pedido de Compra")
    st.markdown("---")
    
    with st.form("pedido"):
        descricao = st.text_area("Descrição do Material*", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            quantidade = st.number_input("Quantidade*", min_value=1, value=1)
        with col2:
            local = st.text_input("Local de Utilização*")
        
        observacoes = st.text_area("Observações", height=80)
        
        st.markdown("---")
        
        if st.form_submit_button("✅ Enviar Pedido", use_container_width=True):
            if descricao and local:
                try:
                    ws = conectar_google_sheets()
                    id_pedido = salvar_pedido(ws, descricao, quantidade, local, observacoes)
                    st.success(f"✅ Pedido #{id_pedido} enviado com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {str(e)}")
            else:
                st.error("⚠️ Preencha os campos obrigatórios (*)")
    
    st.markdown("---")
    st.info("💡 Seu pedido será analisado pelo comprador.")

# Página do Comprador
else:
    st.title("🔒 Área do Comprador")
    st.markdown("---")
    
    # Verificar senha
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            senha = st.text_input("Digite a senha de acesso:", type="password")
            
            if st.button("Acessar", use_container_width=True):
                if senha == SENHA_COMPRADOR:
                    st.session_state.autenticado = True
                    st.success("✅ Acesso concedido!")
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        st.stop()
    
    # Dashboard do Comprador
    st.markdown("## 📋 Gerenciamento de Pedidos")
    
    try:
        ws = conectar_google_sheets()
        df = carregar_pedidos(ws)
        
        if not df.empty:
            # Filtros
            col1, col2 = st.columns(2)
            
            with col1:
                status_filtro = st.multiselect(
                    "Filtrar por status",
                    options=['Aguardando', 'Comprando', 'Entregue', 'Cancelado'],
                    default=['Aguardando', 'Comprando', 'Entregue', 'Cancelado']
                )
            
            with col2:
                busca = st.text_input("🔎 Buscar por descrição do material")
            
            # Aplicar filtros
            df_filtrado = df[df['Status'].isin(status_filtro)]
            
            if busca:
                df_filtrado = df_filtrado[df_filtrado['Descrição'].str.contains(busca, case=False, na=False)]
            
            st.markdown(f"### 📊 Total de pedidos: {len(df_filtrado)}")
            st.markdown("---")
            
            # Exibir cada pedido
            for idx, row in df_filtrado.iterrows():
                status = row['Status']
                
                # Definir cor baseada no status
                if status == 'Aguardando':
                    cor_fundo = "#FFFFFF"
                    cor_borda = "#CCCCCC"
                elif status == 'Comprando':
                    cor_fundo = "#FFF9C4"
                    cor_borda = "#FDD835"
                elif status == 'Entregue':
                    cor_fundo = "#C8E6C9"
                    cor_borda = "#4CAF50"
                else:  # Cancelado
                    cor_fundo = "#FFCDD2"
                    cor_borda = "#F44336"
                
                # Card do pedido
                st.markdown(f"""
                <div style='
                    background-color: {cor_fundo};
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 5px solid {cor_borda};
                    margin-bottom: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                '>
                    <h3 style='margin-top: 0;'>📦 Pedido #{int(row['ID'])}</h3>
                    <p><strong>📝 Descrição:</strong> {row['Descrição']}</p>
                    <p><strong>🔢 Quantidade:</strong> {row['Quantidade']}</p>
                    <p><strong>📍 Local:</strong> {row['Local']}</p>
                    <p><strong>💬 Observações:</strong> {row['Observações'] if row['Observações'] else 'Nenhuma'}</p>
                    <p><strong>📅 Data:</strong> {row['Data']}</p>
                    <p><strong>⚡ Status:</strong> {status}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botões de ação
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button(f"⏳ Aguardando", key=f"ag_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Aguardando'):
                            st.success(f"Pedido #{row['ID']} alterado para AGUARDANDO!")
                            st.rerun()
                
                with col2:
                    if st.button(f"🟡 Comprando", key=f"comp_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Comprando'):
                            st.success(f"Pedido #{row['ID']} alterado para COMPRANDO!")
                            st.rerun()
                
                with col3:
                    if st.button(f"✅ Entregue", key=f"ent_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Entregue'):
                            st.success(f"Pedido #{row['ID']} alterado para ENTREGUE!")
                            st.rerun()
                
                with col4:
                    if st.button(f"❌ Cancelado", key=f"can_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Cancelado'):
                            st.warning(f"Pedido #{row['ID']} CANCELADO!")
                            st.rerun()
                
                st.markdown("---")
            
            # Botão de logout
            if st.button("🚪 Sair da Área do Comprador", use_container_width=True):
                st.session_state.autenticado = False
                st.rerun()
        
        else:
            st.info("📭 Nenhum pedido encontrado no sistema.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
