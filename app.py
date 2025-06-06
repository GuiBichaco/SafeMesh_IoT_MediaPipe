import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
from streamlit_folium import st_folium
import folium
import altair as alt
from streamlit_autorefresh import st_autorefresh

# Configuração inicial
st.set_page_config(page_title="Painel de Alertas", layout="wide")

# Usuário e senha pré-definidos
USUARIO_PRE_DEFINIDO = "admin"
SENHA_PRE_DEFINIDA = "1234"

# Inicializa o estado da sessão para login
if "logado" not in st.session_state:
    st.session_state.logado = False

def realizar_logout():
    """Função para logout do usuário."""
    st.session_state.logado = False
    st.session_state.usuario = None
    st.rerun()

# Tela de Login
if not st.session_state.logado:
    st.title("🔐 Login")

    username = st.text_input("Usuário", value=st.session_state.get("usuario", ""))
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if username == USUARIO_PRE_DEFINIDO and password == SENHA_PRE_DEFINIDA:
            st.session_state.logado = True
            st.session_state.usuario = username
            st.success("Login bem-sucedido! Redirecionando...")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")

    st.stop()  # Interrompe o código caso o usuário não esteja logado

# Botão para Logout
st.sidebar.button("🚪 Sair", on_click=realizar_logout)

# Carrega variáveis do .env
load_dotenv()
API_REPORT = "http://127.0.0.1:8000/reportar_localizacao"

# Auto-refresh a cada 60s
auto_refresh = st.sidebar.checkbox("🔄 Atualizar automaticamente a cada 60s", value=True)
if auto_refresh:
    st_autorefresh(interval=60_000, key="painel_autorefresh")

# Função para obter geolocalização real via IP
@st.cache_data(ttl=300)
def get_geolocation_por_ip():
    try:
        res = requests.get("https://ipinfo.io/json")
        if res.status_code == 200:
            dados = res.json()
            lat, lon = map(float, dados["loc"].split(","))
            return lat, lon
        else:
            return -23.5, -46.6  # fallback São Paulo
    except:
        return -23.5, -46.6  # fallback

# Título
st.title("🚨 Painel de Monitoramento de Alertas")

# Obter localização atual
latitude_centro, longitude_centro = get_geolocation_por_ip()

# Conteúdo principal
with st.container():
    response = requests.get(API_REPORT)
    if response.status_code == 200:
        dados = response.json()
        if isinstance(dados, list) and dados:
            df = pd.DataFrame(dados)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Mapa de alertas
            st.subheader("🗺️ Mapa de Alertas")
            m = folium.Map(location=[latitude_centro, longitude_centro], zoom_start=6)
            for item in df.itertuples():
                folium.Marker(
                    [item.latitude, item.longitude],
                    tooltip=f"{getattr(item, 'cidade', 'Local')}",
                    popup=f"{item.timestamp}",
                    icon=folium.Icon(color="red", icon="exclamation-triangle", prefix='fa')
                ).add_to(m)
            st_folium(m, width=700, height=500)

            # Gráficos
            st.subheader("📊 Distribuição dos Alertas")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Por Cidade**")
                if "cidade" in df.columns:
                    grafico_cidade = alt.Chart(df).mark_bar().encode(
                        x=alt.X("cidade:N", sort='-y'),
                        y="count():Q",
                        tooltip=["cidade:N", "count():Q"]
                    ).properties(height=300)
                    st.altair_chart(grafico_cidade, use_container_width=True)
                else:
                    st.info("Coluna 'cidade' não encontrada.")

            with col2:
                st.markdown("**Por Estado**")
                if "estado" in df.columns:
                    grafico_estado = alt.Chart(df).mark_bar().encode(
                        x=alt.X("estado:N", sort='-y'),
                        y="count():Q",
                        tooltip=["estado:N", "count():Q"]
                    ).properties(height=300)
                    st.altair_chart(grafico_estado, use_container_width=True)
                else:
                    st.info("Coluna 'estado' não encontrada.")

            with col3:
                st.markdown("**Por Tipo de Alerta**")
                if "tipo_alerta" in df.columns:
                    grafico_tipo = alt.Chart(df).mark_bar().encode(
                        x=alt.X("tipo_alerta:N", sort='-y'),
                        y="count():Q",
                        tooltip=["tipo_alerta:N", "count():Q"]
                    ).properties(height=300)
                    st.altair_chart(grafico_tipo, use_container_width=True)
                else:
                    st.info("Coluna 'tipo_alerta' não encontrada.")

            # Tabela de dados
            st.subheader("📄 Dados Brutos")
            st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)
        else:
            st.warning("Nenhum alerta disponível.")
    else:
        st.error(f"Erro ao buscar alertas da API: {response.status_code}")
