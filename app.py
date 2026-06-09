import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Sistema de Pedidos", page_icon="🛒", layout="wide")

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

# Salvar pedido
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

# Interface
st.title("📝 Novo Pedido de Compra")

with st.form("pedido"):
    descricao = st.text_area("Descrição do Material*")
    col1, col2 = st.columns(2)
    with col1:
        quantidade = st.number_input("Quantidade*", min_value=1, value=1)
    with col2:
        local = st.text_input("Local de Utilização*")
    observacoes = st.text_area("Observações")
    
    if st.form_submit_button("Enviar Pedido"):
        if descricao and local:
            ws = conectar_google_sheets()
            id_pedido = salvar_pedido(ws, descricao, quantidade, local, observacoes)
            st.success(f"✅ Pedido #{id_pedido} enviado!")
            st.balloons()
        else:
            st.error("Preencha os campos obrigatórios*")
