import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

st.set_page_config(page_title="Análise de Raio - Lotéricas", layout="wide")
st.title("🎯 Análise de Raio: Lojas vs Lotéricas")
st.markdown("Descubra quais agências lotéricas estão no raio de alcance da sua loja.")

# ==========================================
# 1. CARREGAMENTO E LIMPEZA DOS DADOS
# ==========================================
@st.cache_data
def load_data():
    try:
        df_lojas = pd.read_excel("enderecos_com_coordenadas.xlsx")
        df_lotericas = pd.read_excel("lotericas_enderecos_com_coordenadas.xlsx")
    except FileNotFoundError:
        st.error("⚠️ Arquivos não encontrados na pasta.")
        st.stop()

    df_lojas.columns = df_lojas.columns.str.upper().str.strip()
    df_lotericas.columns = df_lotericas.columns.str.upper().str.strip()

    if 'MUNICÍPIO' in df_lotericas.columns:
        df_lotericas = df_lotericas.rename(columns={'MUNICÍPIO': 'CIDADE'})
    if 'MUNICIPIO' in df_lotericas.columns:
        df_lotericas = df_lotericas.rename(columns={'MUNICIPIO': 'CIDADE'})

    def limpar_coordenadas(df):
        if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns:
            df['LATITUDE'] = pd.to_numeric(df['LATITUDE'].astype(str).str.replace(',', '.'), errors='coerce')
            df['LONGITUDE'] = pd.to_numeric(df['LONGITUDE'].astype(str).str.replace(',', '.'), errors='coerce')
        return df

    df_lojas = limpar_coordenadas(df_lojas)
    df_lotericas = limpar_coordenadas(df_lotericas)

    if 'CIDADE' in df_lojas.columns and 'CIDADE' in df_lotericas.columns:
        df_lojas['CIDADE'] = df_lojas['CIDADE'].astype(str).str.upper().str.strip()
        df_lotericas['CIDADE'] = df_lotericas['CIDADE'].astype(str).str.upper().str.strip()
    else:
        st.error("⚠️ A coluna 'CIDADE' não foi encontrada nas planilhas.")
        st.stop()

    return df_lojas, df_lotericas

df_lojas, df_lotericas = load_data()

# ==========================================
# 2. INTERFACE DE SELEÇÃO
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    cidades_disponiveis = ["🗺️ VISÃO GERAL (TODAS AS LOJAS)"] + sorted(df_lojas['CIDADE'].unique())
    cidade_selecionada = st.selectbox("1️⃣ Escolha a Cidade:", cidades_disponiveis)

# ==========================================
# LÓGICA 1: VISÃO GERAL DO ESTADO (FOLIUM)
# ==========================================
if cidade_selecionada == "🗺️ VISÃO GERAL (TODAS AS LOJAS)":
    st.info("📍 Mostrando todas as lojas no estado. Selecione uma cidade específica acima para fazer a análise de raio com as lotéricas.")

    df_todas_lojas = df_lojas.dropna(subset=['LATITUDE', 'LONGITUDE']).copy()
    col_nome_loja = 'ENDERECO' if 'ENDERECO' in df_todas_lojas.columns else df_todas_lojas.columns[0]

    # Cria o mapa base centrado no RS
    m = folium.Map(location=[-30.0, -53.5], zoom_start=6, tiles="OpenStreetMap")

    # Adiciona os pins azuis para todas as lojas
    for idx, row in df_todas_lojas.iterrows():
        folium.Marker(
            location=[row['LATITUDE'], row['LONGITUDE']],
            tooltip=f"Loja: {row[col_nome_loja]}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    # Renderiza o mapa no Streamlit
    st_folium(m, use_container_width=True, height=600, returned_objects=[])

# ==========================================
# LÓGICA 2: ANÁLISE DE RAIO (FOLIUM)
# ==========================================
else:
    with col2:
        lojas_da_cidade = df_lojas[df_lojas['CIDADE'] == cidade_selecionada]
        col_nome_loja = 'ENDERECO' if 'ENDERECO' in lojas_da_cidade.columns else lojas_da_cidade.columns[0]
        loja_selecionada = st.selectbox("2️⃣ Escolha a sua Loja:", lojas_da_cidade[col_nome_loja].tolist())

    with col3:
        raio_km = st.slider("3️⃣ Defina o Raio de Busca (em KM):", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

    dados_loja = lojas_da_cidade[lojas_da_cidade[col_nome_loja] == loja_selecionada].iloc[0]

    if pd.isna(dados_loja['LATITUDE']) or pd.isna(dados_loja['LONGITUDE']):
        st.error(f"⚠️ A loja {loja_selecionada} está sem coordenadas válidas. Corrija no Excel.")
        st.stop()

    coord_loja = (dados_loja['LATITUDE'], dados_loja['LONGITUDE'])

    lotericas_cidade = df_lotericas[df_lotericas['CIDADE'] == cidade_selecionada].copy()
    lotericas_cidade['LATITUDE'] = pd.to_numeric(lotericas_cidade['LATITUDE'], errors='coerce')
    lotericas_cidade['LONGITUDE'] = pd.to_numeric(lotericas_cidade['LONGITUDE'], errors='coerce')
    lotericas_cidade = lotericas_cidade.dropna(subset=['LATITUDE', 'LONGITUDE'])

    def calcular_distancia(row):
        coord_loterica = (row['LATITUDE'], row['LONGITUDE'])
        return geodesic(coord_loja, coord_loterica).kilometers

    if not lotericas_cidade.empty:
        lotericas_cidade['Distancia_KM'] = lotericas_cidade.apply(calcular_distancia, axis=1)
    else:
        st.warning("Nenhuma lotérica com coordenadas válidas foi encontrada nesta cidade.")

    # Cria o mapa base centrado na loja selecionada
    m = folium.Map(location=[coord_loja[0], coord_loja[1]], zoom_start=14, tiles="OpenStreetMap")

    # DESENHA O CÍRCULO DO RAIO NO MAPA
    folium.Circle(
        location=[coord_loja[0], coord_loja[1]],
        radius=raio_km * 1000, # Converte KM para Metros
        color="#0055FF",
        fill=True,
        fill_color="#0055FF",
        fill_opacity=0.15,
        tooltip=f"Raio de {raio_km}km"
    ).add_to(m)

    # Adiciona o Pin da Loja (Azul com ícone de estrela)
    folium.Marker(
        location=[coord_loja[0], coord_loja[1]],
        tooltip=f"🏢 SUA LOJA: {dados_loja[col_nome_loja]}",
        icon=folium.Icon(color="blue", icon="star")
    ).add_to(m)

    # Adiciona os Pins das Lotéricas
    if not lotericas_cidade.empty:
        col_nome_loterica = 'NOME' if 'NOME' in lotericas_cidade.columns else lotericas_cidade.columns[1]

        for idx, row in lotericas_cidade.iterrows():
            dist = row['Distancia_KM']

            # Define a cor e o ícone baseado na distância
            if dist <= raio_km:
                cor_pino = "green"
                icone_pino = "ok-sign" # Ícone de check
            else:
                cor_pino = "red"
                icone_pino = "remove-sign" # Ícone de X

            folium.Marker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                tooltip=f"🎰 {row[col_nome_loterica]} ({dist:.2f} km)",
                icon=folium.Icon(color=cor_pino, icon=icone_pino)
            ).add_to(m)

    # Renderiza o mapa no Streamlit
    st_folium(m, use_container_width=True, height=600, returned_objects=[])

    # Tabela de Resultados
    if not lotericas_cidade.empty:
        st.subheader(f"📋 Lotéricas num raio de {raio_km}km")
        lotericas_dentro = lotericas_cidade[lotericas_cidade['Distancia_KM'] <= raio_km]

        if not lotericas_dentro.empty:
            tabela_exibicao = lotericas_dentro[[col_nome_loterica, 'Distancia_KM']].sort_values('Distancia_KM')
            tabela_exibicao['Distancia_KM'] = tabela_exibicao['Distancia_KM'].round(2).astype(str) + " km"
            tabela_exibicao.columns = ['Nome da Lotérica', 'Distância']
            st.dataframe(tabela_exibicao, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma lotérica encontrada dentro deste raio. Tente aumentar a distância no controle acima.")