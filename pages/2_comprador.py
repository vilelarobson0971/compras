import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from PIL import Image
from io import BytesIO

SENHA = "brasa@2026"

st.set_page_config(page_title="Gerenciar Pedidos", page_icon="📋", layout="wide")

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
    
    st.page_link("app.py", label="📝 Solicitante", icon="📝")
    st.page_link("pages/2_comprador.py", label="🔒 Comprador", icon="🔒")
    
    st.markdown("---")
    
    if st.session_state.get('logado', False):
        st.caption(f"👤 Logado como: Comprador")
    else:
        st.caption(f"👤 Área restrita")
# ========================================

def formatar_data_br(data_str):
    try:
        if pd.isna(data_str) or data_str == '':
            return ''
        dt = pd.to_datetime(data_str)
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return str(data_str)

def base64_para_imagem(base64_str):
    try:
        if not base64_str or base64_str == '':
            return None
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        image_bytes = base64.b64decode(base64_str)
        return Image.open(BytesIO(image_bytes))
    except Exception as e:
        return None

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
        
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Pedido_Compras")
        return sheet.worksheet("Pedidos")
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")
        return None

def carregar_pedidos(ws):
    try:
        dados = ws.get_all_values()
        if not dados or len(dados) <= 1:
            return []
        
        pedidos = []
        for linha in dados[1:]:
            if len(linha) >= 3 and linha[0] and str(linha[0]).isdigit():
                pedidos.append({
                    'ID': int(linha[0]),
                    'Data': linha[1] if len(linha) > 1 else '',
                    'Descrição': linha[2] if len(linha) > 2 else '',
                    'Quantidade': linha[3] if len(linha) > 3 else '1',
                    'Solicitante': linha[4] if len(linha) > 4 else '',
                    'Local': linha[5] if len(linha) > 5 else '',
                    'Observações': linha[6] if len(linha) > 6 else '',
                    'Foto_Base64': linha[7] if len(linha) > 7 else '',
                    'Status': linha[8] if len(linha) > 8 else 'Aguardando',
                    'Obs_Comprador': linha[10] if len(linha) > 10 else '',
                })
        return pedidos
    except Exception as e:
        st.error(f"Erro ao carregar: {str(e)}")
        return []

def atualizar_status(ws, id_pedido, novo_status):
    try:
        dados = ws.get_all_values()
        for i, linha in enumerate(dados, start=1):
            if linha and len(linha) > 0 and str(linha[0]) == str(id_pedido):
                ws.update_cell(i, 9, novo_status)
                ws.update_cell(i, 10, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return True
        return False
    except Exception as e:
        st.error(f"Erro: {str(e)}")
        return False

def atualizar_observacao_comprador(ws, id_pedido, nova_obs):
    try:
        dados = ws.get_all_values()
        for i, linha in enumerate(dados, start=1):
            if linha and len(linha) > 0 and str(linha[0]) == str(id_pedido):
                # Coluna 11 (K) = Observação interna do comprador
                ws.update_cell(i, 11, nova_obs)
                return True
        return False
    except Exception as e:
        st.error(f"Erro: {str(e)}")
        return False

# Login
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔒 Área Restrita - Comprador")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        senha = st.text_input("Digite a senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if senha == SENHA:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
    st.stop()

st.title("📋 Gerenciamento de Pedidos")

ws = conectar_google_sheets()
if ws is None:
    st.stop()

pedidos = carregar_pedidos(ws)
if not pedidos:
    st.info("Nenhum pedido encontrado")
    st.stop()

df = pd.DataFrame(pedidos)

# Filtros
with st.sidebar:
    st.header("🔍 Filtros")
    status_options = ['Aguardando', 'Comprando', 'Em rota de entrega', 'Entregue', 'Cancelado']
    status_filtro = st.multiselect("Status", status_options, default=['Aguardando', 'Comprando', 'Em rota de entrega'])
    solicitante_filtro = st.selectbox("Solicitante", ['Todos'] + sorted(df['Solicitante'].unique().tolist()))
    apenas_com_foto = st.checkbox("📸 Apenas pedidos com foto")
    
    if st.button("🔄 Recarregar", use_container_width=True):
        st.rerun()

# Aplicar filtros
df_filtrado = df.copy()
if status_filtro:
    df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_filtro)]
if solicitante_filtro != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Solicitante'] == solicitante_filtro]
if apenas_com_foto:
    df_filtrado = df_filtrado[df_filtrado['Foto_Base64'].notna() & (df_filtrado['Foto_Base64'] != '')]

# Estatísticas
st.markdown("### 📊 Resumo")
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total", len(df_filtrado))
with col2:
    st.metric("Aguardando", len(df_filtrado[df_filtrado['Status'] == 'Aguardando']))
with col3:
    st.metric("Comprando", len(df_filtrado[df_filtrado['Status'] == 'Comprando']))
with col4:
    st.metric("Em Rota", len(df_filtrado[df_filtrado['Status'] == 'Em rota de entrega']))
with col5:
    st.metric("Entregues", len(df_filtrado[df_filtrado['Status'] == 'Entregue']))
with col6:
    st.metric("Cancelados", len(df_filtrado[df_filtrado['Status'] == 'Cancelado']))

# Lista de pedidos
st.markdown("### 📦 Lista de Pedidos")

if df_filtrado.empty:
    st.info("Nenhum pedido encontrado com os filtros selecionados.")
else:
    for _, row in df_filtrado.sort_values('ID', ascending=False).iterrows():
        cores = {
            'Aguardando': '#FFF3E0',
            'Comprando': '#FFF9C4',
            'Em rota de entrega': '#E3F2FD',
            'Entregue': '#C8E6C9',
            'Cancelado': '#FFCDD2'
        }
        cor_fundo = cores.get(row['Status'], '#F5F5F5')
        
        with st.container():
            st.markdown(f"""
            <div style='background-color: {cor_fundo}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 5px solid #2196F3;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin: 0;'>📦 Pedido #{row['ID']}</h3>
                    <span style='background-color: #2196F3; color: white; padding: 5px 10px; border-radius: 20px; font-size: 12px;'>{row['Status']}</span>
                </div>
                <hr>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
                    <div>
                        <p><strong>📝 Material:</strong> {row['Descrição']}</p>
                        <p><strong>🔢 Quantidade:</strong> {row['Quantidade']}</p>
                        <p><strong>👤 Solicitante:</strong> {row['Solicitante']}</p>
                        <p><strong>📍 Local:</strong> {row['Local']}</p>
                    </div>
                    <div>
                        <p><strong>📅 Data:</strong> {formatar_data_br(row['Data'])}</p>
                        <p><strong>📝 Observações do Solicitante:</strong> {row['Observações'] if row['Observações'] else '-'}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if row['Foto_Base64'] and row['Foto_Base64'] != '':
                st.markdown("**📸 Foto do item:**")
                img = base64_para_imagem(row['Foto_Base64'])
                if img:
                    st.image(img, use_container_width=False, width=250)
            
            # ===== Campo editável: Observação interna do Comprador =====
            st.markdown("**🗒️ Observação do Comprador (uso interno):**")
            obs_key = f"obs_comprador_{row['ID']}"
            nova_obs_comprador = st.text_area(
                "Anote aqui detalhes importantes deste pedido (ex: prazo, fornecedor, atraso, etc.)",
                value=row['Obs_Comprador'],
                key=obs_key,
                label_visibility="collapsed",
                height=80
            )
            col_salvar, _ = st.columns([1, 4])
            with col_salvar:
                if st.button("💾 Salvar Observação", key=f"salvar_obs_{row['ID']}", use_container_width=True):
                    if atualizar_observacao_comprador(ws, row['ID'], nova_obs_comprador):
                        st.success("Observação salva!")
                        st.rerun()
            # =============================================================
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("⏳ Aguardando", key=f"ag_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Aguardando'):
                        st.rerun()
            with col2:
                if st.button("🟡 Comprando", key=f"comp_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Comprando'):
                        st.rerun()
            with col3:
                if st.button("🚚 Em Rota", key=f"rota_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Em rota de entrega'):
                        st.rerun()
            with col4:
                if st.button("✅ Entregue", key=f"ent_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Entregue'):
                        st.rerun()
            with col5:
                if st.button("❌ Cancelado", key=f"can_{row['ID']}", use_container_width=True):
                    if atualizar_status(ws, row['ID'], 'Cancelado'):
                        st.rerun()
            
            st.divider()
    
    st.caption(f"📊 Mostrando {len(df_filtrado)} pedido(s) de um total de {len(df)}")
