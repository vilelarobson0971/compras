import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

SENHA = "brasa@2026"

# Conectar ao Google Sheets (CORRIGIDO)
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
    return sheet.worksheet("Pedidos")

def carregar_pedidos(ws):
    dados = ws.get_all_records()
    df = pd.DataFrame(dados)
    
    # Garantir que a coluna ID existe e é numérica
    if not df.empty and 'ID' in df.columns:
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
    
    return df

def atualizar_status(ws, id_pedido, novo_status):
    try:
        # Converter para int se necessário
        id_pedido = int(id_pedido)
        
        # Buscar o ID na primeira coluna
        celula = ws.find(str(id_pedido), in_column=1)
        if celula:
            ws.update_cell(celula.row, 7, novo_status)  # Coluna 7 = Status
            ws.update_cell(celula.row, 8, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # Coluna 8 = Ultima_Atualizacao
            return True
        else:
            st.warning(f"Pedido #{id_pedido} não encontrado")
            return False
    except Exception as e:
        st.error(f"Erro ao atualizar status: {str(e)}")
        return False

# Verificar senha
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔒 Área do Comprador")
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# Dashboard
st.title("📋 Gerenciar Pedidos")

try:
    ws = conectar_google_sheets()
    df = carregar_pedidos(ws)
    
    if not df.empty:
        # Verificar se a coluna Status existe
        if 'Status' not in df.columns:
            st.error("A planilha não possui a coluna 'Status'")
            st.stop()
        
        # Filtro por status
        status_options = ['Aguardando', 'Comprando', 'Entregue', 'Cancelado']
        status_presentes = [s for s in status_options if s in df['Status'].values]
        
        if status_presentes:
            status_selecionados = st.multiselect(
                "Filtrar por status", 
                status_options,
                default=status_presentes
            )
        else:
            status_selecionados = st.multiselect(
                "Filtrar por status", 
                status_options,
                default=['Aguardando', 'Comprando']
            )
        
        df_filtrado = df[df['Status'].isin(status_selecionados)]
        
        if df_filtrado.empty:
            st.info("Nenhum pedido encontrado com os filtros selecionados")
        else:
            # Exibir pedidos
            for idx, row in df_filtrado.iterrows():
                cor = {
                    'Aguardando': '#F0F0F0',
                    'Comprando': '#FFF9C4',
                    'Entregue': '#C8E6C9',
                    'Cancelado': '#FFCDD2'
                }.get(row['Status'], '#F0F0F0')
                
                st.markdown(f"""
                <div style='background:{cor}; padding:15px; border-radius:10px; margin:10px 0; border-left:5px solid #ccc;'>
                    <h3>Pedido #{int(row['ID']) if pd.notna(row['ID']) else 'N/A'}</h3>
                    <p><b>Data:</b> {row.get('Data', 'N/A')}</p>
                    <p><b>Material:</b> {row['Descrição']}</p>
                    <p><b>Quantidade:</b> {row['Quantidade']}</p>
                    <p><b>Local:</b> {row['Local']}</p>
                    <p><b>Obs:</b> {row.get('Observações', 'N/A')}</p>
                    <p><b>Status:</b> {row['Status']}</p>
                    <p><b>Última atualização:</b> {row.get('Ultima_Atualizacao', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button(f"⏳ Aguardando", key=f"ag_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Aguardando'):
                            st.success(f"Pedido #{row['ID']} atualizado para Aguardando")
                            st.rerun()
                with col2:
                    if st.button(f"🟡 Comprando", key=f"comp_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Comprando'):
                            st.success(f"Pedido #{row['ID']} atualizado para Comprando")
                            st.rerun()
                with col3:
                    if st.button(f"✅ Entregue", key=f"ent_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Entregue'):
                            st.success(f"Pedido #{row['ID']} atualizado para Entregue")
                            st.rerun()
                with col4:
                    if st.button(f"❌ Cancelado", key=f"can_{row['ID']}"):
                        if atualizar_status(ws, row['ID'], 'Cancelado'):
                            st.success(f"Pedido #{row['ID']} cancelado")
                            st.rerun()
                
                st.markdown("---")
    else:
        st.info("📭 Nenhum pedido encontrado na planilha")
        
except Exception as e:
    st.error(f"Erro ao carregar dados: {str(e)}")
    st.info("Verifique se a planilha 'Pedidos_Compras' existe e está compartilhada com o email de serviço")
