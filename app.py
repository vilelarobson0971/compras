# Substitua a função carregar_logo() por esta versão LOCAL:

def carregar_logo():
    try:
        # Tenta carregar do arquivo local
        img = Image.open("Logo.jpeg")
        return img
    except:
        try:
            img = Image.open("Logo.jpg")
            return img
        except:
            st.warning("⚠️ Arquivo Logo.jpg não encontrado na pasta do projeto")
            return None
