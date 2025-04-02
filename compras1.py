import streamlit as st

# Configuração da página
st.set_page_config(page_title="Rádio Transamérica", page_icon="🎵")

def main():
    st.title("🎵 Rádio Transamérica - Player Online by Robson Vilela")
    
    # URL do streaming
    #stream_url = "https://playerservices.streamtheworld.com/api/livestream-redirect/RT_SPAAC.aac"
    #stream_url = "https://f111.fabricahost.com.br/paiquere917?f=1743554858N01JQSZFKPJFMB6JE77P46PTYFQ&tid=01JQSZFKPJDWRTRSX0ZXX6NCXY"
    #stream_url = "http://up-continental.webnow.com.br/cultura.aac?1743555337315"
    stream_url = "https://antenaone.crossradio.com.br/stream/1;"
    
    # Player de áudio (inicia automaticamente)
    st.audio(stream_url, format='audio/aac')
    st.success("Rádio em reprodução automática!")
    
    # Rodapé
    st.markdown("---")
    st.caption("Player desenvolvido por Robson Vilela | © 2023")

if __name__ == "__main__":
    main()
