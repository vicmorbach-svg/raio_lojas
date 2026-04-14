import streamlit as st
import pandas as pd
import plotly.express as px
from geopy.distance import geodesic

st.set_page_config(page_title="Análise de Raio - Lotéricas", layout="wide")
st.title("📍 Análise de Raio: Lojas vs Lotéricas")

# ==========================================
# 1. CARREGAMENTO DOS DADOS (Simulado para exemplo)
# Substitua pelas suas planilhas reais com Lat/Lon
# ==========================================
@st.cache_data
def load_data():
    # Exemplo de como ler suas planilhas reais:
    df_lojas = pd.read_excel("enderecos_com_coordenadas.xlsx")
    df_lotericas = pd.read_excel("lotericas_enderecos_com_coordenadas.xlsx")

    
    return df_lojas, df_lotericas

df_lojas, df_lotericas = load_data()

# ==========================================
# 2. INTERFACE DE SELEÇÃO
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    cidades_disponiveis = sorted(df_lojas['CIDADE'].unique())
    cidade_selecionada = st.selectbox("1️⃣ Escolha a Cidade:", cidades_disponiveis)

with col2:
    lojas_da_cidade = df_lojas[df_lojas['CIDADE'] == cidade_selecionada]
    loja_selecionada = st.selectbox("2️⃣ Escolha a sua Loja:", lojas_da_cidade['LOJA'].tolist())

with col3:
    raio_km = st.slider("3️⃣ Defina o Raio de Busca (em KM):", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

# ==========================================
# 3. CÁLCULO DE DISTÂNCIA
# ==========================================
# Pega as coordenadas da loja selecionada
dados_loja = lojas_da_cidade[lojas_da_cidade['LOJA'] == loja_selecionada].iloc[0]
coord_loja = (dados_loja['LATITUDE'], dados_loja['LONGITUDE'])

# Filtra as lotéricas da mesma cidade
lotericas_cidade = df_lotericas[df_lotericas['CIDADE'] == cidade_selecionada].copy()

# Calcula a distância de cada lotérica até a loja selecionada
def calcular_distancia(row):
    coord_loterica = (row['LATITUDE'], row['LONGITUDE'])
    return geodesic(coord_loja, coord_loterica).kilometers

if not lotericas_cidade.empty:
    lotericas_cidade['Distancia_KM'] = lotericas_cidade.apply(calcular_distancia, axis=1)

    # Classifica se está dentro ou fora do raio
    lotericas_cidade['Status'] = lotericas_cidade['Distancia_KM'].apply(
        lambda x: f'Dentro do Raio ({raio_km}km)' if x <= raio_km else 'Fora do Raio'
    )
else:
    st.warning("Nenhuma lotérica cadastrada nesta cidade.")

# ==========================================
# 4. CONSTRUÇÃO DO MAPA DE RUAS
# ==========================================
# Prepara os dados da loja para juntar no mapa
df_loja_mapa = pd.DataFrame({
    'NOME': [f"🏢 SUA LOJA: {dados_loja['LOJA']}"],
    'LATITUDE': [dados_loja['LATITUDE']],
    'LONGITUDE': [dados_loja['LONGITUDE']],
    'Status': ['Sua Loja'],
    'Tamanho': [15] # Ponto maior para a loja
})

# Prepara os dados das lotéricas
if not lotericas_cidade.empty:
    lotericas_cidade['Tamanho'] = 10
    df_mapa_final = pd.concat([df_loja_mapa, lotericas_cidade[['NOME', 'LATITUDE', 'LONGITUDE', 'Status', 'Tamanho']]])
else:
    df_mapa_final = df_loja_mapa

# Cores para os pontos
cores = {
    'Sua Loja': '#000000', # Preto
    f'Dentro do Raio ({raio_km}km)': '#00CC00', # Verde
    'Fora do Raio': '#FF0000' # Vermelho
}

fig = px.scatter_mapbox(
    df_mapa_final,
    lat="LATITUDE",
    lon="LONGITUDE",
    color="Status",
    color_discrete_map=cores,
    size="Tamanho",
    hover_name="NOME",
    zoom=13, # Zoom mais próximo para ver as ruas
    center={"lat": coord_loja[0], "lon": coord_loja[1]},
    mapbox_style="open-street-map", # Estilo de mapa com ruas detalhadas
    height=600
)

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. TABELA DE RESULTADOS
# ==========================================
if not lotericas_cidade.empty:
    st.subheader(f"📋 Lotéricas num raio de {raio_km}km")
    lotericas_dentro = lotericas_cidade[lotericas_cidade['Distancia_KM'] <= raio_km]

    if not lotericas_dentro.empty:
        # Formata a tabela para exibição
        tabela_exibicao = lotericas_dentro[['NOME', 'Distancia_KM']].sort_values('Distancia_KM')
        tabela_exibicao['Distancia_KM'] = tabela_exibicao['Distancia_KM'].round(2).astype(str) + " km"
        st.dataframe(tabela_exibicao, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma lotérica encontrada dentro deste raio.")
