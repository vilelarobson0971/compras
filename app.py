import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="Sistema de Pedidos", page_icon="🛒", layout="wide")

# Configurações
SHEET_NAME = "Pedido_Compras"
WORKSHEET_NAME = "Pedidos"

# Conectar ao Google Sheets
@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets e retorna a worksheet"""
    try:
        # Obter os secrets
        segredos = st.secrets["gcp_service_account"]
        
        # Converter para dicionário se necessário
        if isinstance(segredos, str):
            creds_dict = json.loads(segredos)
        else:
            creds_dict = dict(segredos)
        
        # Corrigir quebras de linha na chave privada
        if 'private_key' in creds_dict:
            private_key = creds_dict["private_key"]
            if isinstance(private_key, str):
                private_key = private_key.replace('\\n', '\n')
                creds_dict["private_key"] = private_key
        
        # Escopos necessários
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Criar credenciais e conectar
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME)
        
        # Obter ou criar worksheet
        try:
            worksheet = sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(WORKSHEET_NAME, rows=1000, cols=20)
            # Adicionar cabeçalho
            cabecalho = ['ID', 'Data', 'Descrição', 'Quantidade', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao']
            worksheet.append_row(cabecalho)
        
        return worksheet
    
    except Exception as e:
        st.error(f"❌ Erro ao conectar ao Google Sheets: {str(e)}")
        return None

def obter_proximo_id(ws):
    """Obtém o próximo ID disponível"""
    try:
        dados = ws.get_all_values()
        if len(dados) <= 1:  # Apenas cabeçalho
            return 1
        
        # Pegar todos os IDs da primeira coluna (ignorando cabeçalho)
        ids = []
        for row in dados[1:]:  # Pular cabeçalho
            if row and row[0].isdigit():
                ids.append(int(row[0]))
        
        if not ids:
            return 1
        
        return max(ids) + 1
    
    except Exception as e:
        st.error(f"Erro ao gerar ID: {str(e)}")
        return None

def salvar_pedido(ws, desc, qtd, local, obs):
    """Salva um novo pedido na planilha"""
    try:
        # Validar dados
        if not desc or not local:
            return None
        
        # Obter próximo ID
        novo_id = obter_proximo_id(ws)
        if novo_id is None:
            return None
        
        # Criar linha
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linha = [
            novo_id,
            agora,
            desc.strip(),
            qtd,
            local.strip(),
            obs.strip() if obs else "",
            'Aguardando',
            agora
        ]
        
        # Salvar
        ws.append_row(linha)
        return novo_id
    
    except Exception as e:
        st.error(f"❌ Erro ao salvar pedido: {str(e)}")
        return None

# Interface Principal
st.title("📝 Novo Pedido de Compra")

# Conectar à planilha
ws = conectar_google_sheets()

if ws is None:
    st.error("Não foi possível conectar à planilha. Verifique suas configurações.")
    st.stop()

# Formulário de pedido
with st.form("form_pedido", clear_on_submit=True):
    descricao = st.text_area("📦 Descrição do Material *", height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        quantidade = st.number_input("🔢 Quantidade *", min_value=1, value=1, step=1)
    with col2:
        local = st.text_input("📍 Local de Utilização *", placeholder="Ex: Almoxarifado Central")
    
    observacoes = st.text_area("📝 Observações", placeholder="Informações adicionais...", height=80)
    
    submitted = st.form_submit_button("✅ Enviar Pedido", use_container_width=True)
    
    if submitted:
        if not descricao:
            st.error("⚠️ Por favor, preencha a descrição do material")
        elif not local:
            st.error("⚠️ Por favor, preencha o local de utilização")
        else:
            with st.spinner("Enviando pedido..."):
                id_pedido = salvar_pedido(ws, descricao, quantidade, local, observacoes)
                
                if id_pedido:
                    st.success(f"✅ Pedido #{id_pedido} enviado com sucesso!")
                    st.balloons()
                else:
                    st.error("❌ Erro ao enviar pedido. Tente novamente.")

# Exibir últimos pedidos (opcional)
with st.expander("📋 Ver últimos pedidos"):
    try:
        dados = ws.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            df = df.sort_values('ID', ascending=False).head(5)
            st.dataframe(df[['ID', 'Data', 'Descrição', 'Status']], use_container_width=True)
        else:
            st.info("Nenhum pedido encontrado")
    except Exception as e:
        st.warning(f"Não foi possível carregar os pedidos: {str(e)}")
