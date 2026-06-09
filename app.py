import subprocess
import sys

# Instalar bibliotecas automaticamente
def instalar_bibliotecas():
    bibliotecas = ['streamlit', 'pandas', 'gspread', 'oauth2client']
    for lib in bibliotecas:
        try:
            __import__(lib)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

# Executar instalação
instalar_bibliotecas()

# Agora importar as bibliotecas
import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Sistema de Pedidos", page_icon="🛒", layout="wide")

SENHA_COMPRADOR = "brasa@2026"

# Conectar ao Google Sheets
def conectar_google_sheets():
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
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

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
    try:
        celula = ws.find(str(id_pedido))
        if celula:
            ws.update_cell(celula.row, 7, novo_status)
            ws.update_cell(celula.row, 8, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True
    except:
        pass
    return False

# Menu de navegação
st.sidebar.title("📋 Sistema de Compras")
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
        
        if st.form_submit_button("✅ Enviar Pedido", use_container_width=True):
            if descricao and local:
                ws = conectar_google_sheets()
                if ws:
                    id_pedido = salvar_pedido(ws, descricao, quantidade, local, observacoes)
                    st.success(f"✅ Pedido #{id_pedido} enviado com sucesso!")
                    st.balloons()
                else:
                    st.error("Erro ao conectar com Google Sheets. Verifique as credenciais.")
            else:
                st.error("⚠️ Preencha os campos obrigatórios (*)")

# Página do Comprador
else:
    st.title("🔒 Área do Comprador")
    st.markdown("---")
    
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        senha = st.text_input("Digite a senha de acesso:", type="password")
        
        if st.button("Acessar", use_container_width=True):
            if senha == SENHA_COMPRADOR:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta!")
        st.stop()
    
    ws = conectar_google_sheets()
    if ws:
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
                busca = st.text_input("🔎 Buscar por descrição")
            
            df_filtrado = df[df['Status'].isin(status_filtro)]
            if busca:
                df_filtrado = df_filtrado[df_filtrado['Descrição'].str.contains(busca, case=False, na=False)]
            
            st.markdown(f"### 📊 Total: {len(df_filtrado)} pedidos")
            
            for idx, row in df_filtrado.iterrows():
                status = row['Status']
                cores = {
                    'Aguardando': '#FFFFFF',
                    'Comprando': '#FFF9C4',
                    'Entregue': '#C8E6C9',
                    'Cancelado': '#FFCDD2'
                }
                cor = cores.get(status, '#FFFFFF')
                
                st.markdown(f"""
                <div style='background:{cor}; padding:15px; border-radius:10px; margin:10px 0; border-left:5px solid #ccc;'>
                    <h3>Pedido #{int(row['ID'])}</h3>
                    <p><b>Material:</b> {row['Descrição']}</p>
                    <p><b>Qtd:</b> {row['Quantidade']} | <b>Local:</b> {row['Local']}</p>
                    <p><b>Obs:</b> {row['Observações'] if row['Observações'] else '-'}</p>
                    <p><b>Status:</b> {status}</p>
                </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(4)
                botoes = ['Aguardando', 'Comprando', 'Entregue', 'Cancelado']
                for col, btn in zip(cols, botoes):
                    if col.button(f"{btn}", key=f"{btn}_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], btn):
                            st.rerun()
                st.markdown("---")
            
            if st.button("Sair", use_container_width=True):
                st.session_state.autenticado = False
                st.rerun()
        else:
            st.info("Nenhum pedido encontrado")
