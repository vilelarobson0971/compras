import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
from PIL import Image
import os

st.set_page_config(
    page_title="Sistema de Pedidos - Infralink", 
    page_icon="🛒",
    layout="wide"
)

# Configuração do Drive - COLOQUE O ID DA SUA PASTA AQUI
PASTA_DRIVE_ID = "1LjLATf8vQvWZjvZqQDfyGALXq1ck2VC5j"

# Função para obter data/hora local do Brasil (GMT-3)
def obter_data_hora_brasil():
    utc_now = datetime.utcnow()
    brasilia_now = utc_now - timedelta(hours=3)
    return brasilia_now

# Função para formatar data para exibição
def formatar_data_br(data_str):
    try:
        if pd.isna(data_str) or data_str == '':
            return ''
        dt = pd.to_datetime(data_str)
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return str(data_str)

# Função para carregar a logo local
def carregar_logo():
    try:
        if os.path.exists("Logo.jpeg"):
            img = Image.open("Logo.jpeg")
            return img
        elif os.path.exists("Logo.jpg"):
            img = Image.open("Logo.jpg")
            return img
        else:
            return None
    except Exception as e:
        return None

# Conectar ao Google Drive
def conectar_google_drive():
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
        
        scope = ['https://www.googleapis.com/auth/drive.file']
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.warning(f"⚠️ Drive não conectado: {str(e)}")
        return None

# Função para fazer upload da imagem para o Google Drive
def upload_imagem_drive(service, imagem_bytes, nome_arquivo, pasta_id):
    try:
        if not pasta_id or pasta_id == "SEU_ID_DA_PASTA_AQUI":
            return None
        
        temp_path = f"/tmp/{nome_arquivo}"
        with open(temp_path, "wb") as f:
            f.write(imagem_bytes)
        
        file_metadata = {
            'name': nome_arquivo,
            'parents': [pasta_id]
        }
        
        media = MediaFileUpload(temp_path, mimetype='image/jpeg', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # Tornar público
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        os.remove(temp_path)
        return f"https://drive.google.com/uc?id={file['id']}"
    except Exception as e:
        st.warning(f"⚠️ Erro no upload da foto: {str(e)}")
        return None

# Função para corrigir a estrutura da planilha
def corrigir_estrutura_planilha(ws):
    try:
        cabecalho = ws.row_values(1)
        ordem_correta = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Foto_Link', 'Status', 'Ultima_Atualizacao']
        
        if cabecalho != ordem_correta:
            st.info("🔄 Corrigindo estrutura da planilha...")
            
            # Obter todos os dados
            dados = ws.get_all_values()
            
            # Mapear índices atuais
            idx_id = cabecalho.index('ID') if 'ID' in cabecalho else 0
            idx_data = cabecalho.index('Data') if 'Data' in cabecalho else 1
            idx_desc = cabecalho.index('Descrição') if 'Descrição' in cabecalho else 2
            idx_qtd = cabecalho.index('Quantidade') if 'Quantidade' in cabecalho else 3
            idx_solicitante = cabecalho.index('Solicitante') if 'Solicitante' in cabecalho else 4
            idx_local = cabecalho.index('Local') if 'Local' in cabecalho else 5
            idx_obs = cabecalho.index('Observações') if 'Observações' in cabecalho else 6
            
            # Verificar onde está o Status
            if 'Status' in cabecalho:
                idx_status = cabecalho.index('Status')
            elif 'Aguardando' in dados[1] if len(dados) > 1 else False:
                # Status pode estar na coluna 8
                idx_status = 7
            else:
                idx_status = 8
            
            # Limpar planilha
            ws.clear()
            
            # Escrever novo cabeçalho
            ws.append_row(ordem_correta)
            
            # Migrar dados
            for row in dados[1:]:
                if len(row) > 0:
                    nova_linha = [
                        row[idx_id] if idx_id < len(row) else '',
                        row[idx_data] if idx_data < len(row) else '',
                        row[idx_desc] if idx_desc < len(row) else '',
                        row[idx_qtd] if idx_qtd < len(row) else '',
                        row[idx_solicitante] if idx_solicitante < len(row) else '',
                        row[idx_local] if idx_local < len(row) else '',
                        row[idx_obs] if idx_obs < len(row) else '',
                        '',  # Foto_Link (vazio)
                        row[idx_status] if idx_status < len(row) else 'Aguardando',
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    ws.append_row(nova_linha)
            
            st.success("✅ Estrutura corrigida!")
        
        return True
    except Exception as e:
        st.error(f"Erro ao corrigir estrutura: {str(e)}")
        return False

# Conectar ao Google Sheets
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
        
        try:
            worksheet = sheet.worksheet("Pedidos")
            corrigir_estrutura_planilha(worksheet)
        except:
            worksheet = sheet.add_worksheet("Pedidos", 1000, 20)
            cabecalho = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Foto_Link', 'Status', 'Ultima_Atualizacao']
            worksheet.append_row(cabecalho)
            st.info("✅ Planilha criada!")
        
        return worksheet
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {str(e)}")
        return None

def obter_proximo_id(ws):
    try:
        dados = ws.get_all_values()
        if len(dados) <= 1:
            return 1
        ids = []
        for row in dados[1:]:
            if row and row[0] and str(row[0]).isdigit():
                ids.append(int(row[0]))
        return max(ids) + 1 if ids else 1
    except:
        return 1

def salvar_pedido(ws, desc, qtd, solicitante, local, obs, foto_link=None):
    try:
        novo_id = obter_proximo_id(ws)
        agora_brasil = obter_data_hora_brasil()
        agora_str = agora_brasil.strftime("%Y-%m-%d %H:%M:%S")
        
        # Ordem correta das colunas
        linha = [
            novo_id,
            agora_str,
            desc.strip(),
            qtd,
            solicitante.strip(),
            local.strip(),
            obs.strip() if obs else "",
            foto_link if foto_link else "",
            'Aguardando',
            agora_str
        ]
        
        ws.append_row(linha)
        return novo_id
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {str(e)}")
        return None

# ==================== INTERFACE ====================

logo = carregar_logo()

col_logo, col_title = st.columns([1, 5])

with col_logo:
    if logo:
        st.image(logo, width=100)
    else:
        st.markdown("📦")

with col_title:
    st.title("📝 Pedidos de Compra")
    st.markdown("**By Robson Vilela 2026**")
    st.caption("Preencha o formulário abaixo para solicitar um novo pedido")

st.divider()

ws = conectar_google_sheets()
if ws is None:
    st.stop()

drive_service = conectar_google_drive()

with st.container():
    st.markdown("### 📋 Novo Pedido de Compra")
    
    with st.form("form_pedido", clear_on_submit=True):
        descricao = st.text_area("📦 Descrição do Material *", height=80)
        
        col1, col2 = st.columns(2)
        with col1:
            quantidade = st.number_input("🔢 Quantidade *", min_value=1, value=1)
        with col2:
            solicitante = st.text_input("👤 Solicitante *")
        
        local = st.text_input("📍 Local de Utilização *")
        observacoes = st.text_area("📝 Observações", height=60)
        
        st.markdown("---")
        st.markdown("### 📸 Foto do Item (Opcional)")
        
        foto_upload = st.file_uploader("Clique para adicionar uma foto", type=['jpg', 'jpeg', 'png'])
        
        if foto_upload:
            st.image(Image.open(foto_upload), caption="Pré-visualização", width=150)
        
        st.markdown("---")
        
        if st.form_submit_button("✅ Enviar Pedido", use_container_width=True):
            if not descricao or not solicitante or not local:
                st.error("⚠️ Preencha os campos obrigatórios")
            else:
                with st.spinner("Enviando..."):
                    foto_link = None
                    if foto_upload and drive_service:
                        nome_arquivo = f"pedido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        foto_link = upload_imagem_drive(drive_service, foto_upload.getvalue(), nome_arquivo, PASTA_DRIVE_ID)
                        if foto_link:
                            st.success("📸 Foto anexada!")
                    
                    id_pedido = salvar_pedido(ws, descricao, quantidade, solicitante, local, observacoes, foto_link)
                    
                    if id_pedido:
                        st.success(f"✅ Pedido #{id_pedido} enviado!")
                        st.balloons()
                        st.rerun()

st.divider()

with st.expander("📋 Ver últimos pedidos", expanded=False):
    try:
        dados = ws.get_all_values()
        if dados and len(dados) > 1:
            for registro in dados[1:6]:  # Últimos 5
                if len(registro) >= 6:
                    st.write(f"**#{registro[0]}** - {registro[2]} - {registro[4]} - {registro[8] if len(registro) > 8 else 'Aguardando'}")
                    st.divider()
        else:
            st.info("Nenhum pedido encontrado")
    except Exception as e:
        st.warning(f"Erro: {str(e)}")

st.divider()
st.caption(f"© {datetime.now().year} - By Robson Vilela")
