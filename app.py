import streamlit as st
import pandas as pd
from datetime import datetime
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
            
            # Se tiver as colunas mas invertidas (Solicitante e Local trocados)
            if 'Solicitante' in cabecalho and 'Local' in cabecalho:
                # Recriar a planilha com a estrutura correta
                st.info("🔄 Reorganizando as colunas da planilha...")
                
                # Obter todos os dados existentes
                dados = ws.get_all_values()
                
                # Mapear índices das colunas
                idx_id = cabecalho.index('ID') if 'ID' in cabecalho else 0
                idx_data = cabecalho.index('Data') if 'Data' in cabecalho else 1
                idx_desc = cabecalho.index('Descrição') if 'Descrição' in cabecalho else 2
                idx_qtd = cabecalho.index('Quantidade') if 'Quantidade' in cabecalho else 3
                idx_solicitante = cabecalho.index('Solicitante') if 'Solicitante' in cabecalho else 4
                idx_local = cabecalho.index('Local') if 'Local' in cabecalho else 5
                idx_obs = cabecalho.index('Observações') if 'Observações' in cabecalho else 6
                idx_status = cabecalho.index('Status') if 'Status' in cabecalho else 7
                idx_atualizacao = cabecalho.index('Ultima_Atualizacao') if 'Ultima_Atualizacao' in cabecalho else 8
                
                # Limpar a planilha atual
                ws.clear()
                
                # Escrever novo cabeçalho na ordem correta
                ws.append_row(ordem_correta)
                
                # Migrar os dados existentes para a nova estrutura
                for row in dados[1:]:  # Pular cabeçalho antigo
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
            # Corrigir estrutura da planilha existente
            corrigir_estrutura_planilha(worksheet)
        except:
            # Criar nova planilha com a estrutura correta
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
        
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ordem correta: ID, Data, Descrição, Quantidade, Solicitante, Local, Observações, Status, Ultima_Atualizacao
        linha = [
            novo_id,
            agora,
            desc.strip(),
            qtd,
            solicitante.strip(),
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
        st.image(logo, use_container_width=True)
    else:
        st.markdown("""
        <div style="width:100%;aspect-ratio:1;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);border-radius:15px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
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

# Formulário de pedido com layout aprimorado
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
        
        # Botões alinhados
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
                        st.rerun()  # Recarregar para mostrar o novo pedido
                    else:
                        st.error("❌ Erro ao enviar pedido. Tente novamente.")

st.divider()

# Exibir últimos pedidos com visual aprimorado
with st.expander("📋 Ver últimos pedidos", expanded=False):
    try:
        dados = ws.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            df = df.sort_values('ID', ascending=False).head(5)
            
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%d/%m/%Y %H:%M')
            
            # Colunas para exibir na ordem correta
            colunas_para_exibir = ['ID', 'Data', 'Descrição', 'Solicitante', 'Local', 'Status']
            colunas_existentes = [col for col in colunas_para_exibir if col in df.columns]
            
            # Renomear colunas para exibição mais amigável
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

# Rodapé profissional
st.divider()
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer2:
    st.caption(f"© {datetime.now().year} - Infralink Sistema de Pedidos de Compra v1.0")
