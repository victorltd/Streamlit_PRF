import streamlit as st
import pandas as pd
import plotly.express as px

#importando bibliotecas
import geopandas as gpd
import matplotlib.pyplot as plt
#importar os objetos geometros da biblioteca shapely
from shapely.geometry import Point, LineString, Polygon
#importar plugin FastMakerCluster
import folium
from folium.plugins import FastMarkerCluster
from folium.plugins import HeatMap
import plotly.express as px
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Dashboard de Acidentes - PE", layout="wide")

# Barra de navegação
with st.sidebar:
    selected = option_menu(
        menu_title="Menu Principal",  # required
        options=["Página Inicial", "Perfil das pessoas envolvidas", "Veículos envolvidos"],  # required
        icons=["house", "bar-chart", "map"],  # optional
        menu_icon="cast",  # optional
        default_index=0,  # optional
    )

st.title("Acidentes nas Estradas em 2024 - PE (PRF)")

# Carregar os dados
@st.cache_data
def load_data():
    return pd.read_csv('df_detran_detalhe_filtrado.csv', delimiter=';', encoding='UTF-8')

df_detran = load_data()
data = gpd.read_file('dados/PE_Municipios_2023.json', driver='GeoJSON')

# Filtrar o GeoDataFrame com base no nome do município
nome_estado = 'PE'
df_detran = df_detran[df_detran['uf'] == nome_estado]

#criando df para analise das pessoas
df_detran_pessoas=df_detran.drop_duplicates(subset='pesid', keep='first')


# Agrupar por 'id' (acidente) e 'id_veiculo' (veículo)
df_veiculos = df_detran.groupby(['id', 'id_veiculo']).agg({
    'tipo_veiculo': 'first',  # Pegar o tipo do veículo (é o mesmo para todas as vítimas do mesmo veículo)
    'marca': 'first',         # Pegar a marca do veículo
    'ano_fabricacao_veiculo': 'first',  # Pegar o ano de fabricação do veículo
    'latitude': 'first',      # Pegar a latitude do acidente
    'longitude': 'first'      # Pegar a longitude do acidente
}).reset_index()

#pego esse dataframe e deixo ele somente para analisar os acidentes

df_detran=df_detran.drop_duplicates(subset='id', keep='first')



# Replace commas with dots and convert to float
df_detran['latitude'] = df_detran['latitude'].str.replace(',', '.').astype(float)
df_detran['longitude'] = df_detran['longitude'].str.replace(',', '.').astype(float)
df_detran['br'] = df_detran['br'].astype(str)

# Criar a coluna geometry usando as coordenadas convertidas
df_detran['geometry'] = df_detran.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)

# Criar GeoDataFrame
gdf_detran = gpd.GeoDataFrame(df_detran, geometry='geometry')

media_lat = gdf_detran['latitude'].mean()
media_lon = gdf_detran['longitude'].mean()





if(selected == "Página Inicial"):
    # 1. Métricas Gerais (Cards)
    #st.header("Métricas Gerais")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Acidentes", df_detran.shape[0])
    col2.metric("Total de Vítimas Fatais", df_detran_pessoas['mortos'].sum())
    col3.metric("Total de Feridos", df_detran_pessoas['feridos_leves'].sum() + df_detran['feridos_graves'].sum())
    col4.metric("Total de veiculos", df_veiculos.shape[0])

    # 2. Visão Geral dos Acidentes
    st.header("Visão Geral dos Acidentes")
    col5, col6 = st.columns([1, 1])
    with col5:

        st.subheader("Mapa de Cluster de Acidentes")
        fmap = folium.Map(location=[media_lat, media_lon], zoom_start=7, tiles='cartodbpositron')
        limites = folium.GeoJson(data, style_function=lambda feature: {'fillColor': 'white', 'color': 'black', 'weight': 1, 'fillOpacity': 0.5})
        fmap.add_child(limites)
        mc = FastMarkerCluster(gdf_detran[['latitude', 'longitude']])
        fmap.add_child(mc)
        st_folium(fmap, width=700, height=400)
    with col6:
        #st.subheader("Evolução Temporal dos Acidentes")
        df_detran['data_inversa'] = pd.to_datetime(df_detran['data_inversa'], format='%Y-%m-%d')
        df_temporal = df_detran.groupby('data_inversa').size().reset_index(name='Numero acidentes')
        fig = px.line(df_temporal, x='data_inversa', y='Numero acidentes', title='Acidentes por Data')
        st.plotly_chart(fig)

    # 3. Análise por Localização
    st.header("Análise por Localização")
    col7, col8, col9 = st.columns([1, 1, 1])
    with col7:
        #st.subheader("Top 5 BRs com Mais Acidentes Graves")
        df_graves = df_detran[df_detran['classificacao_acidente'].isin(['Com Vítimas Fatais', 'Com Vítimas Feridas'])]
        top_br = df_graves['br'].value_counts().nlargest(5).reset_index()
        top_br.columns = ['BR', 'Numero acidentes graves']
        fig = px.bar(top_br, x='BR', y='Numero acidentes graves', title='BRs com mais acidentes graves')
        fig.update_layout(xaxis=dict(type='category'))

        st.plotly_chart(fig)
    with col8:
        #st.subheader("Top 5 Municípios com Mais Acidentes Graves")
        cidade_graves = df_graves['municipio'].value_counts().nlargest(5).reset_index()
        cidade_graves.columns = ['Municipio', 'Numero acidentes graves']
        fig = px.bar(cidade_graves, x='Municipio', y='Numero acidentes graves', title='Cidades com mais acidentes graves')
        st.plotly_chart(fig)
    with col9:
        #st.subheader("Trechos com Mais Acidentes Graves")
        br_km_graves = df_graves.groupby(['br', 'km']).size().nlargest(10).reset_index(name='Numero acidentes graves')
        fig = px.bar(br_km_graves, x='km', y='Numero acidentes graves', title='Top 10 trechos com mais acidentes graves', hover_data=['br'])
        fig.update_layout(xaxis=dict(type='category'))

        st.plotly_chart(fig)

    # 4. Análise por Causas e Fatores
    st.header("Análise por Causas e Fatores")
    col10, col11, col12 = st.columns([2, 1, 1])
    with col10:
        #st.subheader("Principais Causas de Acidentes")
        causas = df_detran['causa_acidente'].value_counts().nlargest(10).reset_index()
        causas.columns = ['Causa', 'Numero acidentes']
        fig = px.pie(causas, values='Numero acidentes', names='Causa', title='Principais causas de acidentes')
        st.plotly_chart(fig)
    with col11:
        #st.subheader("Acidentes Graves por Condição Meteorológica")
        meteorologia_graves = df_graves['condicao_metereologica'].value_counts().reset_index()
        meteorologia_graves.columns = ['Condicao metereologica', 'Numero acidentes graves']
        fig = px.bar(meteorologia_graves, x='Condicao metereologica', y='Numero acidentes graves', title='Acidentes graves por condicao metereologica')
        st.plotly_chart(fig)
    with col12:
        #st.subheader("Acidentes Graves por Tipo de Pista")
        pista_graves = df_graves['tipo_pista'].value_counts().reset_index()
        pista_graves.columns = ['Pista', 'Numero acidentes graves']
        fig = px.pie(pista_graves, names='Pista', values='Numero acidentes graves', title='Acidentes graves por tipo de pista')
        st.plotly_chart(fig)

    # 5. Análise por Tempo e Período
    st.header("Análise por Tempo e Período")
    col13, col14, col15= st.columns([1, 1, 1])
    with col13:
        #st.subheader("Acidentes Graves por Dia da Semana")
        dia_semama_graves = df_graves['dia_semana'].value_counts().reset_index()
        dia_semama_graves.columns = ['Dia da semana', 'Numero acidentes graves']
        fig = px.bar(dia_semama_graves, x='Dia da semana', y='Numero acidentes graves', title='Acidentes graves por dia da semana')
        st.plotly_chart(fig)
    with col14:
        #st.subheader("Acidentes Graves por Fase do Dia")
        fase_dia_graves = df_graves['fase_dia'].value_counts().reset_index()
        fase_dia_graves.columns = ['Fase do dia', 'Numero acidentes graves']
        fig = px.bar(fase_dia_graves, x='Fase do dia', y='Numero acidentes graves', title='Acidentes graves por fase do dia')
        st.plotly_chart(fig)

    with col15:
        # Classificar os dias como fim de semana ou dia útil
        df_detran['tipo_dia_semana'] = df_detran['data_inversa'].apply(lambda x: 'Fim de Semana' if x.weekday() >= 5 else 'Dia Útil')

        # Contar o número de acidentes em finais de semana vs. dias úteis
        acidentes_fim_semana = df_detran[df_detran['tipo_dia_semana'] == 'Fim de Semana'].shape[0]
        acidentes_dia_util = df_detran[df_detran['tipo_dia_semana'] == 'Dia Útil'].shape[0]

        # Criar gráfico de barras
        fig = px.bar(x=['Fim de Semana', 'Dia Útil'], y=[acidentes_fim_semana, acidentes_dia_util], 
                    labels={'x': 'Tipo de Dia', 'y': 'Número de Acidentes'}, 
                    title='Acidentes em Finais de Semana vs. Dias Úteis')
        st.plotly_chart(fig)

    # 6. Detalhes Adicionais
    st.header("Detalhes Adicionais")
    col15, col16 = st.columns([1, 1])
    with col15:
        #st.subheader("Média de Pessoas Envolvidas por Acidente")
        total_pessoas=df_detran['feridos_leves'].sum() + df_detran['feridos_graves'].sum() + df_detran['mortos'].sum() + df_detran['ilesos'].sum()

        media_pessoas = (df_detran['feridos_leves'].sum() + df_detran['feridos_graves'].sum() + df_detran['mortos'].sum() + df_detran['ilesos'].sum()) / df_detran.shape[0]

        st.write(f"A média de pessoas envolvidas em acidentes é de {media_pessoas:.2f}")
        totais = {'Mortos': df_detran['mortos'].sum(), 'Feridos graves': df_detran['feridos_graves'].sum(), 
                'Feridos leves': df_detran['feridos_leves'].sum(), 'Ilesos': df_detran['ilesos'].sum()}
        fig = px.pie(values=list(totais.values()), names=list(totais.keys()), title='Proporcao de mortos, feridos graves, feridos leves e ilesos')
        st.plotly_chart(fig)
    with col16:
    
        st.subheader("Mapa de Calor de Acidentes")
        fmap = folium.Map(location=[media_lat, media_lon], zoom_start=7, tiles='cartodbpositron')
        heat_map = HeatMap(gdf_detran[['latitude', 'longitude']], radius=15)
        fmap.add_child(heat_map)
        st_folium(fmap, width=700, height=400)

if(selected == "Perfil das pessoas envolvidas"):
    st.write("Página Perfil das pessoas envolvidas")

    col1, col2= st.columns([1, 2])

    with col1:
        sexo_distribuicao = df_detran_pessoas['sexo'].value_counts().reset_index()
        sexo_distribuicao.columns = ['Sexo', 'Número de Vítimas']
        fig = px.pie(sexo_distribuicao, values='Número de Vítimas', names='Sexo', title='Distribuição de Vítimas por Sexo')
        st.plotly_chart(fig)

    with col2:
        # Remover onde tem NaN e ordenar
        df_detran_pessoas = df_detran_pessoas.dropna(subset=['idade']).sort_values(by='idade')
        fig = px.histogram(df_detran_pessoas, x='idade', nbins=20, title='Distribuição de Vítimas por Idade', labels={'idade': 'Idade'})
        fig.update_layout(xaxis=dict(type='category'))
        st.plotly_chart(fig)

    col3, col4 = st.columns([1, 1])

    with col3:
        estado_fisico_distribuicao = df_detran_pessoas['estado_fisico'].value_counts().reset_index()
        estado_fisico_distribuicao.columns = ['Estado Físico', 'Número de Vítimas']
        fig = px.bar(estado_fisico_distribuicao, x='Estado Físico', y='Número de Vítimas', title='Estado Físico das Vítimas')
        st.plotly_chart(fig)

    with col4:
        tipo_envolvido_distribuicao = df_detran_pessoas['tipo_envolvido'].value_counts().reset_index()
        tipo_envolvido_distribuicao.columns = ['Tipo de Envolvido', 'Número de Vítimas']
        fig = px.pie(tipo_envolvido_distribuicao, values='Número de Vítimas', names='Tipo de Envolvido', title='Tipo de Envolvido das Vítimas')
        st.plotly_chart(fig)

    col5, col6 = st.columns([1, 1])

    with col5:
        index_to_remove = df_detran_pessoas[df_detran_pessoas['idade'] == 1024].index

        fig = px.box(df_detran_pessoas.drop(index_to_remove), x='estado_fisico', y='idade', title='Relação entre Idade e Estado Físico', labels={'estado_fisico': 'Estado Físico', 'idade': 'Idade'})
        st.plotly_chart(fig)

    with col6:
        fig = px.bar(df_detran_pessoas, x='tipo_veiculo', color='estado_fisico', title='Relação entre Tipo de Veículo e Estado Físico', labels={'tipo_veiculo': 'Tipo de Veículo', 'estado_fisico': 'Estado Físico'})
        st.plotly_chart(fig)

    col7, col8, col9 = st.columns([1, 1,1])

    with col7:
        tipo_sexo_distribuicao = df_detran_pessoas.groupby(['tipo_envolvido', 'sexo']).size().reset_index(name='Número de Vítimas')
        fig = px.bar(tipo_sexo_distribuicao, x='tipo_envolvido', y='Número de Vítimas', color='sexo', title='Proporção de Vítimas por Tipo de Envolvido e Sexo')
        st.plotly_chart(fig)

    with col8:
        fig = px.box(df_detran_pessoas.drop(index_to_remove), x='tipo_envolvido', y='idade', title='Distribuição de Idade por Tipo de Envolvido', labels={'tipo_envolvido': 'Tipo de Envolvido', 'idade': 'Idade'})
        st.plotly_chart(fig)

    with col9:
        media_idade_estado = df_detran_pessoas.groupby('estado_fisico')['idade'].mean().reset_index()
        fig = px.bar(media_idade_estado, x='estado_fisico', y='idade', title='Média de Idade por Estado Físico', labels={'estado_fisico': 'Estado Físico', 'idade': 'Média de Idade'})
        st.plotly_chart(fig)

    col10, col11 = st.columns([1, 1])

    with col10:
        tipo_estado_distribuicao = df_detran_pessoas.groupby(['tipo_veiculo', 'estado_fisico']).size().reset_index(name='Número de Vítimas')
        fig = px.bar(tipo_estado_distribuicao, x='tipo_veiculo', y='Número de Vítimas', color='estado_fisico', title='Proporção de Vítimas por Tipo de Veículo e Estado Físico')
        st.plotly_chart(fig)

    with col11:
        tipo_estado_distribuicao = df_detran_pessoas.groupby(['tipo_envolvido', 'estado_fisico']).size().reset_index(name='Número de Vítimas')
        fig = px.bar(tipo_estado_distribuicao, x='tipo_envolvido', y='Número de Vítimas', color='estado_fisico', title='Proporção de Vítimas por Tipo de Envolvido e Estado Físico')
        st.plotly_chart(fig)

if(selected == "Veículos envolvidos"):

    

    col1, col2 = st.columns([2, 1])

    with col1:
        tipo_veiculo_distribuicao = df_veiculos['tipo_veiculo'].value_counts().reset_index()
        tipo_veiculo_distribuicao.columns = ['Tipo de Veículo', 'Número de Veículos']

        # Criar gráfico de barras
        fig = px.bar(tipo_veiculo_distribuicao, x='Tipo de Veículo', y='Número de Veículos', title='Tipos de Veículos Envolvidos em Acidentes')
        st.plotly_chart(fig)

    with col2:
        df_veiculos = df_veiculos.sort_values(by='ano_fabricacao_veiculo')
        fig = px.histogram(df_veiculos, x='ano_fabricacao_veiculo', nbins=20, title='Ano de Fabricação dos Veículos Envolvidos', labels={'ano_fabricacao_veiculo': 'Ano de Fabricação'})
        fig.update_layout(xaxis=dict(type='category'))
        st.plotly_chart(fig)

    col3, col4 = st.columns([1, 1])

    with col3:
        df_veiculos['marca'] = df_veiculos['marca'].fillna('')
        df_veiculos[['marca_carro', 'modelo']] = df_veiculos['marca'].str.split('/', expand=True, n=1)

        # Contar o número de veículos por marca
        marca_distribuicao = df_veiculos['marca_carro'].value_counts().nlargest(10).reset_index()
        marca_distribuicao.columns = ['Marca', 'Número de Veículos']

        # Criar gráfico de barras
        fig = px.bar(marca_distribuicao, x='Marca', y='Número de Veículos', title='Marcas de Veículos Envolvidos em Acidentes')
        st.plotly_chart(fig)

    with col4:
        # Contar o número de veículos por modelo
        modelo_distribuicao = df_veiculos['modelo'].value_counts().nlargest(10).reset_index()
        modelo_distribuicao.columns = ['Modelo', 'Número de Veículos']

        # Criar gráfico de barras
        fig = px.bar(modelo_distribuicao, x='Modelo', y='Número de Veículos', title='Modelos de Veículos Envolvidos em Acidentes')
        st.plotly_chart(fig)

    col5, col6 , col7= st.columns([1, 1,1])

    with col5:
        # Contar o número de veículos por tipo de veículo e marca
        tipo_marca_distribuicao = df_veiculos.groupby(['tipo_veiculo', 'marca_carro']).size().reset_index(name='Número de Veículos')

        # Criar gráfico de barras
        fig = px.bar(tipo_marca_distribuicao, x='tipo_veiculo', y='Número de Veículos', color='marca_carro', title='Proporção de Veículos por Tipo e Marca')
        st.plotly_chart(fig)

    with col6:
        df_motocicletas = df_veiculos[df_veiculos['tipo_veiculo'] == 'Motocicleta']
        modelo_distri = df_motocicletas['modelo'].value_counts().nlargest(10).reset_index()
        modelo_distri.columns = ['Modelo', 'Número de Veículos']

        fig = px.bar(modelo_distri, x='Modelo', y='Número de Veículos', title='Modelos de Motocicletas Envolvidos em Acidentes')
        st.plotly_chart(fig)

    with col7:
        df_carros = df_veiculos[df_veiculos['tipo_veiculo'] == 'Automóvel']
        modelo_distri = df_carros['modelo'].value_counts().nlargest(10).reset_index()
        modelo_distri.columns = ['Modelo', 'Número de Veículos']

        fig = px.bar(modelo_distri, x='Modelo', y='Número de Veículos', title='Modelos de Automóveis Envolvidos em Acidentes')
        st.plotly_chart(fig)



