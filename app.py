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
import io
import base64

st.set_page_config(
    page_title="Sistema de Pedidos - Infralink", 
    page_icon="🛒",
    layout="wide"
)

# Configuração do Drive
PASTA_DRIVE_ID = "1LjLATf8vQvWZjvZqQDfyGALXq1ck2VC5j"  # Você precisa criar uma pasta no Google Drive e colocar o ID aqui

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
        
        scope = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"❌ Erro ao conectar ao Google Drive: {str(e)}")
        return None

# Função para fazer upload da imagem para o Google Drive
def upload_imagem_drive(service, imagem_bytes, nome_arquivo, pasta_id):
    """Faz upload da imagem para o Google Drive e retorna o link"""
    try:
        # Salvar temporariamente
        temp_path = f"/tmp/{nome_arquivo}"
        with open(temp_path, "wb") as f:
            f.write(imagem_bytes)
        
        # Configurar metadata
        file_metadata = {
            'name': nome_arquivo,
            'parents': [pasta_id]
        }
        
        # Fazer upload
        media = MediaFileUpload(temp_path, mimetype='image/jpeg', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
        
        # Tornar o arquivo público (opcional)
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Limpar arquivo temporário
        os.remove(temp_path)
        
        # Retornar link de visualização
        return f"https://drive.google.com/uc?id={file['id']}"
    except Exception as e:
        st.error(f"❌ Erro ao fazer upload da imagem: {str(e)}")
        return None

# Função para corrigir a estrutura da planilha se necessário
def corrigir_estrutura_planilha(ws):
    try:
        cabecalho = ws.row_values(1)
        ordem_correta = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Foto_Link', 'Status', 'Ultima_Atualizacao']
        
        if cabecalho != ordem_correta:
            st.warning("⚠️ Atualizando estrutura da planilha para incluir fotos...")
            
            if len(cabecalho) < 9:
                # Adicionar coluna de foto
                ws.add_cols(1)
                ws.update_cell(1, 9, 'Foto_Link')
                st.success("✅ Coluna 'Foto_Link' adicionada!")
            
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
            st.info("✅ Planilha 'Pedidos' criada com suporte a fotos!")
        
        return worksheet
    
    except gspread.SpreadsheetNotFound:
        st.error("""
        ❌ Planilha 'Pedido_Compras' não encontrada!
        
        Verifique se:
        1. O nome exato da planilha é 'Pedido_Compras'
        2. Ela foi compartilhada com o email de serviço
        3. A permissão é de 'Editor'
        """)
        return None
    
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
            if row and row[0].isdigit():
                ids.append(int(row[0]))
        
        if not ids:
            return 1
        
        return max(ids) + 1
    except Exception as e:
        st.error(f"Erro ao gerar ID: {str(e)}")
        return None

def salvar_pedido(ws, desc, qtd, solicitante, local, obs, foto_link=None):
    try:
        if not desc or not local or not solicitante:
            return None
        
        novo_id = obter_proximo_id(ws)
        if novo_id is None:
            return None
        
        agora_brasil = obter_data_hora_brasil()
        agora_str = agora_brasil.strftime("%Y-%m-%d %H:%M:%S")
        
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
        st.error(f"❌ Erro ao salvar pedido: {str(e)}")
        return None

# ==================== INTERFACE PROFISSIONAL ====================

logo = carregar_logo()

col_logo, col_title = st.columns([1, 5])

with col_logo:
    if logo:
        st.image(logo, width=120)
    else:
        st.markdown("""
        <div style="width:120px;height:120px;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);border-radius:15px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <span style="color:white;font-size:48px;">📦</span>
        </div>
        """, unsafe_allow_html=True)

with col_title:
    st.title("📝 Pedidos de Compra")
    st.markdown("**By Robson Vilela 2026**")
    st.caption("Preencha o formulário abaixo para solicitar um novo pedido")

st.divider()

ws = conectar_google_sheets()

if ws is None:
    st.error("Não foi possível conectar à planilha. Verifique suas configurações.")
    st.stop()

# Conectar ao Drive para upload de fotos
drive_service = conectar_google_drive()

with st.container():
    st.markdown("### 📋 Novo Pedido de Compra")
    
    with st.form("form_pedido", clear_on_submit=True):
        descricao = st.text_area("📦 Descrição do Material *", height=100, 
                                 placeholder="Ex: Parafuso sextavado 5/16 x 1\" - Aço carbono")
        
        col1, col2 = st.columns(2)
        with col1:
            quantidade = st.number_input("🔢 Quantidade *", min_value=1, value=1, step=1)
        with col2:
            solicitante = st.text_input("👤 Solicitante *", 
                                        placeholder="Nome completo ou matrícula")
        
        col3, col4 = st.columns(2)
        with col3:
            local = st.text_input("📍 Local de Utilização *", 
                                  placeholder="Ex: Almoxarifado Central | Obra X | Setor Y")
        with col4:
            st.markdown("")
        
        observacoes = st.text_area("📝 Observações", 
                                   placeholder="Informações adicionais sobre o pedido...", 
                                   height=80)
        
        # Upload de foto (OPCIONAL)
        st.markdown("---")
        st.markdown("### 📸 Foto do Item (Opcional)")
        st.caption("Tire uma foto ou selecione da galeria para ajudar o comprador a identificar o item")
        
        foto_upload = st.file_uploader(
            "Clique para adicionar uma foto", 
            type=['jpg', 'jpeg', 'png', 'gif'],
            help="Formatos aceitos: JPG, PNG, GIF. Tamanho máximo: 5MB"
        )
        
        foto_preview = None
        if foto_upload:
            # Mostrar preview
            foto_preview = Image.open(foto_upload)
            st.image(foto_preview, caption="Pré-visualização da foto", width=200)
        
        st.markdown("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
        with col_btn2:
            submitted = st.form_submit_button("✅ Enviar Pedido", use_container_width=True)
        
        if submitted:
            if not descricao:
                st.error("⚠️ Por favor, preencha a descrição do material")
            elif not solicitante:
                st.error("⚠️ Por favor, preencha o nome do solicitante")
            elif not local:
                st.error("⚠️ Por favor, preencha o local de utilização")
            else:
                with st.spinner("Enviando pedido..."):
                    foto_link = None
                    
                    # Fazer upload da foto se houver
                    if foto_upload:
                        if drive_service:
                            nome_arquivo = f"pedido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            foto_bytes = foto_upload.getvalue()
                            foto_link = upload_imagem_drive(drive_service, foto_bytes, nome_arquivo, PASTA_DRIVE_ID)
                            if foto_link:
                                st.success("📸 Foto anexada com sucesso!")
                            else:
                                st.warning("⚠️ Não foi possível anexar a foto, mas o pedido será enviado")
                    
                    id_pedido = salvar_pedido(ws, descricao, quantidade, solicitante, local, observacoes, foto_link)
                    
                    if id_pedido:
                        st.success(f"✅ Pedido #{id_pedido} enviado com sucesso por {solicitante}!")
                        if foto_link:
                            st.info("📸 A foto foi anexada ao pedido e estará disponível para o comprador")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Erro ao enviar pedido. Tente novamente.")

st.divider()

with st.expander("📋 Ver últimos pedidos", expanded=False):
    try:
        dados = ws.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            df = df.sort_values('ID', ascending=False).head(5)
            
            if 'Data' in df.columns:
                df['Data'] = df['Data'].apply(formatar_data_br)
            
            colunas_para_exibir = ['ID', 'Data', 'Descrição', 'Solicitante', 'Local', 'Status']
            colunas_existentes = [col for col in colunas_para_exibir if col in df.columns]
            
            df_exibicao = df[colunas_existentes].copy()
            df_exibicao.columns = ['ID', 'Data', 'Descrição', 'Solicitante', 'Local', 'Status']
            
            st.dataframe(
                df_exibicao, 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum pedido encontrado")
    except Exception as e:
        st.warning(f"Não foi possível carregar os pedidos: {str(e)}")

st.divider()
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer2:
    st.caption(f"© {datetime.now().year} - By Robson Vilela")
