import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
from PIL import Image
import os

st.set_page_config(
    page_title="Sistema de Pedidos - Infralink", 
    page_icon="🛒",
    layout="wide"
)

# Função para obter data/hora local do Brasil (GMT-3)
def obter_data_hora_brasil():
    """Retorna a data e hora atual no fuso horário de Brasília (GMT-3)"""
    # UTC atual
    utc_now = datetime.utcnow()
    # Subtrair 3 horas para GMT-3 (Brasília)
    brasilia_now = utc_now - timedelta(hours=3)
    return brasilia_now

# Função para formatar data para exibição
def formatar_data_br(data_str):
    """Formata data do formato ISO para DD/MM/YYYY HH:MM"""
    try:
        if pd.isna(data_str) or data_str == '':
            return ''
        # Converter para datetime
        dt = pd.to_datetime(data_str)
        # Formatar para brasileiro
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return str(data_str)

# Função para carregar a logo local
def carregar_logo():
    """Carrega a logo do arquivo local Logo.jpeg"""
    try:
        if os.path.exists("Logo.jpeg"):
            img = Image.open("Logo.jpeg")
            return img
        elif os.path.exists("Logo.jpg"):
            img = Image.open("Logo.jpg")
            return img
        else:
            st.warning("⚠️ Arquivo Logo.jpeg não encontrado na pasta do projeto")
            return None
    except Exception as e:
        st.warning(f"⚠️ Erro ao carregar a logo: {str(e)}")
        return None

# Função para corrigir a estrutura da planilha se necessário
def corrigir_estrutura_planilha(ws):
    """Verifica e corrige a ordem das colunas da planilha"""
    try:
        cabecalho = ws.row_values(1)
        
        # Ordem correta das colunas
        ordem_correta = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao']
        
        # Verificar se o cabeçalho está na ordem correta
        if cabecalho != ordem_correta:
            st.warning("⚠️ Estrutura da planilha detectada fora do padrão. Corrigindo...")
            
            if 'Solicitante' in cabecalho and 'Local' in cabecalho:
                st.info("🔄 Reorganizando as colunas da planilha...")
                
                dados = ws.get_all_values()
                
                idx_id = cabecalho.index('ID') if 'ID' in cabecalho else 0
                idx_data = cabecalho.index('Data') if 'Data' in cabecalho else 1
                idx_desc = cabecalho.index('Descrição') if 'Descrição' in cabecalho else 2
                idx_qtd = cabecalho.index('Quantidade') if 'Quantidade' in cabecalho else 3
                idx_solicitante = cabecalho.index('Solicitante') if 'Solicitante' in cabecalho else 4
                idx_local = cabecalho.index('Local') if 'Local' in cabecalho else 5
                idx_obs = cabecalho.index('Observações') if 'Observações' in cabecalho else 6
                idx_status = cabecalho.index('Status') if 'Status' in cabecalho else 7
                idx_atualizacao = cabecalho.index('Ultima_Atualizacao') if 'Ultima_Atualizacao' in cabecalho else 8
                
                ws.clear()
                ws.append_row(ordem_correta)
                
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
                            row[idx_status] if idx_status < len(row) else '',
                            row[idx_atualizacao] if idx_atualizacao < len(row) else ''
                        ]
                        ws.append_row(nova_linha)
                
                st.success("✅ Estrutura da planilha corrigida com sucesso!")
                return True
            
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
            cabecalho = ['ID', 'Data', 'Descrição', 'Quantidade', 'Solicitante', 'Local', 'Observações', 'Status', 'Ultima_Atualizacao']
            worksheet.append_row(cabecalho)
            st.info("✅ Planilha 'Pedidos' criada com a estrutura correta!")
        
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
    """Obtém o próximo ID disponível"""
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

def salvar_pedido(ws, desc, qtd, solicitante, local, obs):
    """Salva um novo pedido na planilha - ordem correta"""
    try:
        if not desc or not local or not solicitante:
            return None
        
        novo_id = obter_proximo_id(ws)
        if novo_id is None:
            return None
        
        # Usar data/hora do Brasil (GMT-3)
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
    # st.markdown("**By Robson Vilela 2026**")
    st.caption("Preencha o formulário abaixo para solicitar um novo pedido")

st.divider()

ws = conectar_google_sheets()

if ws is None:
    st.error("Não foi possível conectar à planilha. Verifique suas configurações.")
    st.stop()

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
                                   placeholder="Informações adicionais sobre o pedido (prazo, fornecedor, etc.)...", 
                                   height=80)
        
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
                    id_pedido = salvar_pedido(ws, descricao, quantidade, solicitante, local, observacoes)
                    
                    if id_pedido:
                        st.success(f"✅ Pedido #{id_pedido} enviado com sucesso por {solicitante}!")
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
                # Formatar data para padrão brasileiro
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
    st.caption(f"© {datetime.now().year} - Robson Vilela")
