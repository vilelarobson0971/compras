import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(
    page_title="Sistema de Pedidos - Infralink", 
    page_icon="🛒",
    layout="wide"
)

# Função para carregar a logo do GitHub com múltiplas tentativas
def carregar_logo():
    # Lista de possíveis URLs para tentar
    urls_tentar = [
        "https://raw.githubusercontent.com/vilelaborbson0971/compras/main/Logo.jpeg",
        "https://raw.githubusercontent.com/vilelaborbson0971/compras/main/Logo.jpg",
        "https://raw.githubusercontent.com/vilelaborbson0971/compras/main/logo.jpeg",
        "https://raw.githubusercontent.com/vilelaborbson0971/compras/main/logo.jpg",
        "https://github.com/vilelaborbson0971/compras/blob/main/Logo.jpeg?raw=true",
    ]
    
    for url in urls_tentar:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                st.success(f"✅ Logo carregada com sucesso!")
                return img
        except:
            continue
    
    st.warning("⚠️ Logo não encontrada. Verifique se o arquivo está no repositório.")
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
            cabecalho = ['ID', 'Data', 'Descrição', 'Quantidade', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao']
            worksheet.append_row(cabecalho)
            st.info("✅ Planilha 'Pedidos' criada automaticamente!")
        
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
            if row and row[0].isdigit():
                ids.append(int(row[0]))
        
        if not ids:
            return 1
        
        return max(ids) + 1
    
    except Exception as e:
        st.error(f"Erro ao gerar ID: {str(e)}")
        return None

def salvar_pedido(ws, desc, qtd, local, obs):
    try:
        if not desc or not local:
            return None
        
        novo_id = obter_proximo_id(ws)
        if novo_id is None:
            return None
        
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
        
        ws.append_row(linha)
        return novo_id
    
    except Exception as e:
        st.error(f"❌ Erro ao salvar pedido: {str(e)}")
        return None

# ==================== INTERFACE PROFISSIONAL ====================

# Carregar logo
logo = carregar_logo()

# Layout do cabeçalho com logo e título
col_logo, col_title = st.columns([1, 5])

with col_logo:
    if logo:
        st.image(logo, width=120)
    else:
        # Mostrar um ícone personalizado quando a logo não carrega
        st.markdown("""
        <div style="width:120px;height:120px;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);border-radius:15px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <span style="color:white;font-size:48px;">📦</span>
        </div>
        """, unsafe_allow_html=True)

with col_title:
    st.title("📝 Sistema de Pedidos de Compra")
    st.markdown("**Infralink - Gestão de Compras**")
    st.caption("Preencha o formulário abaixo para solicitar um novo pedido")

st.divider()

# Conectar à planilha
ws = conectar_google_sheets()

if ws is None:
    st.error("Não foi possível conectar à planilha. Verifique suas configurações.")
    st.stop()

# Formulário de pedido
with st.container():
    st.markdown("### 📋 Novo Pedido de Compra")
    
    with st.form("form_pedido", clear_on_submit=True):
        descricao = st.text_area("📦 Descrição do Material *", height=100, 
                                 placeholder="Ex: Parafuso sextavado 5/16 x 1\" - Aço carbono")
        
        col1, col2 = st.columns(2)
        with col1:
            quantidade = st.number_input("🔢 Quantidade *", min_value=1, value=1, step=1)
        with col2:
            local = st.text_input("📍 Local de Utilização *", 
                                  placeholder="Ex: Almoxarifado Central | Obra X | Setor Y")
        
        observacoes = st.text_area("📝 Observações", 
                                   placeholder="Informações adicionais sobre o pedido...", 
                                   height=80)
        
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
        with col_btn2:
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

st.divider()

# Exibir últimos pedidos
with st.expander("📋 Ver últimos pedidos", expanded=False):
    try:
        dados = ws.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            df = df.sort_values('ID', ascending=False).head(5)
            
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(
                df[['ID', 'Data', 'Descrição', 'Status']], 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum pedido encontrado")
    except Exception as e:
        st.warning(f"Não foi possível carregar os pedidos: {str(e)}")

# Rodapé
st.divider()
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer2:
    st.caption(f"© {datetime.now().year} - Infralink Sistema de Pedidos de Compra v1.0")
