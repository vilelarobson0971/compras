import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="Sistema de Pedidos", page_icon="🛒", layout="wide")

# Conectar ao Google Sheets
def conectar_google_sheets():
    # Obter os secrets
    segredos = st.secrets["gcp_service_account"]
    
    # Converter para dicionário se necessário
    if isinstance(segredos, str):
        creds_dict = json.loads(segredos)
    else:
        creds_dict = dict(segredos)
    
    # Garantir que as quebras de linha estão corretas na chave privada
    if 'private_key' in creds_dict:
        private_key = creds_dict["private_key"]
        if isinstance(private_key, str):
            # Substituir \n literal por quebras de linha reais
            private_key = private_key.replace('\\n', '\n')
            creds_dict["private_key"] = private_key
    
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
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
    novo_id = len(dados)  # Correção: usar len(dados) em vez de len(dados) + 1
    
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
            try:
                ws = conectar_google_sheets()
                id_pedido = salvar_pedido(ws, descricao, quantidade, local, observacoes)
                st.success(f"✅ Pedido #{id_pedido} enviado com sucesso!")
                st.balloons()
                # Limpar formulário (opcional)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao enviar pedido: {str(e)}")
        else:
            st.error("Preencha os campos obrigatórios*")
