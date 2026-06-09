import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SENHA = "brasa@2026"

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
    return sheet.worksheet("Pedidos")

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

# Verificar senha
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔒 Área do Comprador")
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# Dashboard
st.title("📋 Gerenciar Pedidos")
ws = conectar_google_sheets()
df = carregar_pedidos(ws)

if not df.empty:
    # Filtro por status
    status = st.multiselect("Filtrar por status", 
                           ['Aguardando', 'Comprando', 'Entregue', 'Cancelado'],
                           default=['Aguardando', 'Comprando', 'Entregue', 'Cancelado'])
    
    df_filtrado = df[df['Status'].isin(status)]
    
    # Exibir pedidos
    for idx, row in df_filtrado.iterrows():
        cor = {
            'Aguardando': 'white',
            'Comprando': '#FFF9C4',
            'Entregue': '#C8E6C9',
            'Cancelado': '#FFCDD2'
        }.get(row['Status'], 'white')
        
        st.markdown(f"""
        <div style='background:{cor}; padding:15px; border-radius:10px; margin:10px 0; border-left:5px solid #ccc;'>
            <h3>Pedido #{row['ID']}</h3>
            <p><b>Material:</b> {row['Descrição']}</p>
            <p><b>Quantidade:</b> {row['Quantidade']}</p>
            <p><b>Local:</b> {row['Local']}</p>
            <p><b>Obs:</b> {row['Observações']}</p>
            <p><b>Status:</b> {row['Status']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button(f"⏳ Aguardando", key=f"ag_{row['ID']}"):
                atualizar_status(ws, row['ID'], 'Aguardando')
                st.rerun()
        with col2:
            if st.button(f"🟡 Comprando", key=f"comp_{row['ID']}"):
                atualizar_status(ws, row['ID'], 'Comprando')
                st.rerun()
        with col3:
            if st.button(f"✅ Entregue", key=f"ent_{row['ID']}"):
                atualizar_status(ws, row['ID'], 'Entregue')
                st.rerun()
        with col4:
            if st.button(f"❌ Cancelado", key=f"can_{row['ID']}"):
                atualizar_status(ws, row['ID'], 'Cancelado')
                st.rerun()
        
        st.markdown("---")
else:
    st.info("Nenhum pedido encontrado")
