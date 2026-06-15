import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
from PIL import Image
import os
import base64
from io import BytesIO

st.set_page_config(
    page_title="Sistema de Pedidos - Infralink", 
    page_icon="🛒",
    layout="wide"
)

# ========== ESCONDER MENU PADRÃO ==========
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ========== MENU PERSONALIZADO ==========
with st.sidebar:
    st.markdown("### 📋 Menu Principal")
    st.markdown("---")
    
    # Menu atual (Solicitante)
    st.page_link("app.py", label="📝 Solicitante", icon="📝")
    st.page_link("pages/2_comprador.py", label="🔒 Comprador", icon="🔒")
    
    st.markdown("---")
    
    # Informação do usuário
    st.caption(f"👤 Logado como: Solicitante")
# ========================================

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

# Função para converter imagem para Base64
def imagem_para_base64(imagem_bytes):
    try:
        img = Image.open(BytesIO(imagem_bytes))
        img.thumbnail((500, 500))
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_base64}"
    except Exception as e:
        st.warning(f"Erro ao converter imagem: {str(e)}")
        return None

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
        except:
            worksheet = sheet.add_worksheet("Pedidos", 1000, 20)
            cabecalho = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Foto_Base64', 'Status', 'Ultima_Atualizacao']
            worksheet.append_row(cabecalho)
            st.info("✅ Planilha 'Pedidos' criada!")
        
        return worksheet
    
    except gspread.SpreadsheetNotFound:
        st.error("""
        ❌ Planilha 'Pedido_Compras' não encontrada!
        
        Verifique se:
        1. O nome exato da planilha é 'Pedido_Compras'
        2. Ela foi compartilhada com o email: bot-planilha@infralinkcompras.iam.gserviceaccount.com
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
            if row and row[0] and str(row[0]).isdigit():
                ids.append(int(row[0]))
        
        return max(ids) + 1 if ids else 1
    except Exception as e:
        return 1

def salvar_pedido(ws, desc, qtd, solicitante, local, obs, foto_base64=None):
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
            foto_base64 if foto_base64 else "",
            'Aguardando',
            agora_str
        ]
        
        ws.append_row(linha)
        return novo_id
    except Exception as e:
        st.error(f"❌ Erro ao salvar pedido: {str(e)}")
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
    st.markdown("**Desenvolvedor Robson Vilela**")
    st.caption("Preencha o formulário abaixo para solicitar um novo pedido")

st.divider()

ws = conectar_google_sheets()

if ws is None:
    st.error("Não foi possível conectar à planilha. Verifique suas configurações.")
    st.stop()

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
        st.caption("Tire uma foto ou selecione da galeria")
        
        foto_upload = st.file_uploader("Clique para adicionar uma foto", type=['jpg', 'jpeg', 'png'])
        
        foto_base64 = None
        if foto_upload:
            foto_base64 = imagem_para_base64(foto_upload.getvalue())
            if foto_base64:
                st.image(Image.open(foto_upload), caption="Pré-visualização", width=150)
                st.success("✅ Foto carregada com sucesso!")
        
        st.markdown("---")
        
        if st.form_submit_button("✅ Enviar Pedido", use_container_width=True):
            if not descricao:
                st.error("⚠️ Por favor, preencha a descrição do material")
            elif not solicitante:
                st.error("⚠️ Por favor, preencha o nome do solicitante")
            elif not local:
                st.error("⚠️ Por favor, preencha o local de utilização")
            else:
                with st.spinner("Enviando pedido..."):
                    id_pedido = salvar_pedido(ws, descricao, quantidade, solicitante, local, observacoes, foto_base64)
                    
                    if id_pedido:
                        if foto_base64:
                            st.success(f"✅ Pedido #{id_pedido} enviado com sucesso com foto!")
                        else:
                            st.success(f"✅ Pedido #{id_pedido} enviado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Erro ao enviar pedido. Tente novamente.")

st.divider()

# ========== ÚLTIMOS PEDIDOS (ATUALIZADO) ==========
with st.expander("📋 Ver últimos pedidos", expanded=True):
    st.markdown("### 📦 Últimos 10 Pedidos Ativos")
    st.caption("Mostrando apenas pedidos em Aguardando, Comprando ou Em rota de entrega")
    
    try:
        dados = ws.get_all_values()
        if dados and len(dados) > 1:
            # Coletar todos os pedidos
            pedidos_lista = []
            for registro in dados[1:]:
                if len(registro) >= 9:
                    status = registro[8] if len(registro) > 8 else 'Aguardando'
                    # Filtrar: não mostrar Cancelados ou Entregues
                    if status not in ['Cancelado', 'Entregue']:
                        pedidos_lista.append({
                            'ID': registro[0],
                            'Data': registro[1] if len(registro) > 1 else '',
                            'Descrição': registro[2] if len(registro) > 2 else '',
                            'Solicitante': registro[4] if len(registro) > 4 else '',
                            'Status': status
                        })
            
            # Ordenar por ID decrescente e pegar os 10 últimos
            pedidos_lista.sort(key=lambda x: int(x['ID']), reverse=True)
            pedidos_lista = pedidos_lista[:10]
            
            if pedidos_lista:
                # Criar DataFrame para exibição
                df_pedidos = pd.DataFrame(pedidos_lista)
                
                # Formatar data
                df_pedidos['Data'] = df_pedidos['Data'].apply(formatar_data_br)
                
                # Mapear cores para os status
                def cor_status(status):
                    cores = {
                        'Aguardando': '🟡',
                        'Comprando': '🟠',
                        'Em rota de entrega': '🔵'
                    }
                    return cores.get(status, '⚪')
                
                df_pedidos['Status'] = df_pedidos['Status'].apply(lambda x: f"{cor_status(x)} {x}")
                
                # Renomear colunas para exibição
                df_pedidos = df_pedidos.rename(columns={
                    'ID': 'Nº',
                    'Data': 'Data/Hora',
                    'Descrição': 'Material',
                    'Solicitante': 'Solicitante',
                    'Status': 'Status'
                })
                
                # Exibir tabela
                st.dataframe(
                    df_pedidos,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nº": st.column_config.TextColumn("Nº", width="small"),
                        "Data/Hora": st.column_config.TextColumn("Data/Hora", width="medium"),
                        "Material": st.column_config.TextColumn("Material", width="large"),
                        "Solicitante": st.column_config.TextColumn("Solicitante", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="medium"),
                    }
                )
                
                # Mostrar quantidade
                st.caption(f"📊 Mostrando {len(pedidos_lista)} pedido(s) ativos (excluídos: Entregues e Cancelados)")
            else:
                st.info("📭 Nenhum pedido ativo encontrado")
        else:
            st.info("📭 Nenhum pedido encontrado")
    except Exception as e:
        st.warning(f"Erro ao carregar pedidos: {str(e)}")

st.divider()
st.caption(f"© {datetime.now().year} - Desenvolvedor Robson Vilela")
