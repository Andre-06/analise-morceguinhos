import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="WhatsApp Analyzer", layout="wide")
st.title("📊 Análise dos Morcegos Pequenos")

# --- LEITURA DIRETA DO ARQUIVO ---
CAMINHO_ARQUIVO = "Conversa do WhatsApp com morceguinhos.txt"

try:
    with open(CAMINHO_ARQUIVO, "r", encoding="utf-8") as file:
        data = file.read()
except FileNotFoundError:
    st.error(
        f"Arquivo '{CAMINHO_ARQUIVO}' não encontrado. Certifique-se de que ele está na mesma pasta do script ou informe o caminho correto.")
    st.stop()

# --- EXTRAÇÃO INICIAL (REGEX) ---
padrao = r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}) - ([^:]+): (.*)'
linhas = data.split('\n')
dados_limpos = []

for linha in linhas:
    match = re.match(padrao, linha)
    if match:
        data_hora, autor, mensagem = match.groups()
        dados_limpos.append({
            "Data_Hora": data_hora,
            "Autor": autor.strip(),
            "Mensagem": mensagem.strip()
        })

df_completo = pd.DataFrame(dados_limpos)

if not df_completo.empty:
    # --- TRATAMENTO DOS DADOS E ORDENAÇÃO ---
    df_completo['Data_Hora'] = pd.to_datetime(df_completo['Data_Hora'], format='%d/%m/%Y %H:%M', errors='coerce')
    if df_completo['Data_Hora'].isna().all():
        df_completo['Data_Hora'] = pd.to_datetime(df_completo['Data_Hora'], errors='coerce')

    # Ordenar por tempo cronológico (essencial para as métricas sequenciais)
    df_completo = df_completo.dropna(subset=['Data_Hora']).sort_values(by='Data_Hora').reset_index(drop=True)

    # Criação de features temporais e estatísticas básicas
    df_completo['Hora'] = df_completo['Data_Hora'].dt.hour
    df_completo['Dia_Semana'] = df_completo['Data_Hora'].dt.day_name()
    df_completo['Ano_Mes'] = df_completo['Data_Hora'].dt.to_period('M').astype(str)
    df_completo['Qtd_Palavras'] = df_completo['Mensagem'].apply(lambda x: len(x.split()))
    df_completo['Contem_Link'] = df_completo['Mensagem'].apply(lambda x: 1 if 'http' in x or 'www.' in x else 0)
    df_completo['Eh_Midia'] = df_completo['Mensagem'].apply(lambda x: 1 if '<Mídia omitida>' in x else 0)

    # Mapeamento dos dias para português
    dias_pt = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df_completo['Dia_Semana'] = df_completo['Dia_Semana'].map(dias_pt)


    # Classificação por Turno do Dia
    def categorizar_turno(hora):
        if 0 <= hora < 6:
            return 'Madrugada 🦉'
        elif 6 <= hora < 12:
            return 'Manhã ☕'
        elif 12 <= hora < 18:
            return 'Tarde ☀️'
        else:
            return 'Noite 🌙'


    df_completo['Turno'] = df_completo['Hora'].apply(categorizar_turno)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros de Análise")
    usuarios_disponiveis = ["Todos do Grupo"] + list(df_completo['Autor'].unique())
    usuario_selecionado = st.sidebar.selectbox("Selecione um integrante:", usuarios_disponiveis)

    # Aplicação do filtro global
    if usuario_selecionado == "Todos do Grupo":
        df = df_completo
    else:
        df = df_completo[df_completo['Autor'] == usuario_selecionado]

    st.success(f"Dados carregados! Analisando: **{usuario_selecionado}**")

    # --- SEÇÃO 1: MÉTRICAS GERAIS ---
    st.header("📈 Visão Geral")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Mensagens", f"{len(df):,}")
    m2.metric("Integrantes Ativos", df['Autor'].nunique() if usuario_selecionado == "Todos do Grupo" else 1)
    m3.metric("Média de Palavras/Msg", f"{df['Qtd_Palavras'].mean():.1f}")
    m4.metric("Links Compartilhados", df['Contem_Link'].sum())

    st.markdown("---")

    # --- SEÇÃO 2: RANKINGS DOS INTEGRANTES (Apenas visão global) ---
    if usuario_selecionado == "Todos do Grupo":
        st.header("🏆 Ranking dos Integrantes")
        col_rank1, col_rank2 = st.columns(2)

        with col_rank1:
            st.subheader("Quem manda mais mensagens?")
            top_autores = df['Autor'].value_counts().reset_index()
            top_autores.columns = ['Autor', 'Mensagens']
            fig_autores = px.bar(top_autores.head(15), x='Mensagens', y='Autor', orientation='h',
                                 title="Top 15 Usuários", color='Mensagens', color_continuous_scale='Viridis')
            fig_autores.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_autores, use_container_width=True)

        with col_rank2:
            st.subheader("Quem escreve mais textão?")
            media_palavras = df.groupby('Autor')['Qtd_Palavras'].mean().reset_index()
            media_palavras = media_palavras.sort_values(by='Qtd_Palavras', ascending=False)
            fig_textao = px.bar(media_palavras.head(15), x='Qtd_Palavras', y='Autor', orientation='h',
                                title="Média de palavras por mensagem", color='Qtd_Palavras',
                                color_continuous_scale='Cividis')
            fig_textao.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_textao, use_container_width=True)

        st.markdown("---")

        # --- SEÇÃO 3: ANÁLISE TEMPORAL ---
        st.header("🕒 Análise de Horários e Linha do Tempo")
        col_temp1, col_temp2 = st.columns(2)

        with col_temp1:
            st.subheader("Atividade por Hora do Dia")
            msg_por_hora = df['Hora'].value_counts().sort_index().reset_index()
            msg_por_hora.columns = ['Hora', 'Mensagens']
            fig_hora = px.line(msg_por_hora, x='Hora', y='Mensagens', title="Picos de atividade ao longo do dia",
                               markers=True)
            fig_hora.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
            st.plotly_chart(fig_hora, use_container_width=True)

        with col_temp2:
            st.subheader("Atividade por Dia da Semana")
            ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            msg_dia = df['Dia_Semana'].value_counts().reindex(ordem_dias).reset_index()
            msg_dia.columns = ['Dia da Semana', 'Mensagens']
            fig_dia = px.bar(msg_dia, x='Dia da Semana', y='Mensagens', title="Mensagens acumuladas por dia",
                             color='Mensagens')
            st.plotly_chart(fig_dia, use_container_width=True)

        st.subheader("📅 Histórico de Mensagens por Mês")
        msg_por_mes = df['Ano_Mes'].value_counts().sort_index().reset_index()
        msg_por_mes.columns = ['Mês', 'Mensagens']

        if not msg_por_mes.empty:
            fig_mes = px.line(msg_por_mes, x='Mês', y='Mensagens', title="Volume de conversas ao longo dos meses",
                              markers=True, color_discrete_sequence=['#25D366'])
            fig_mes.update_xaxes(tickangle=45)
            st.plotly_chart(fig_mes, use_container_width=True)
        else:
            st.info("Dados de data insuficientes para gerar o gráfico mensal.")

        st.markdown("---")

    # --- SEÇÃO 4: CONFIGURAÇÃO DE STOPWORDS E TRATAMENTO TEXTUAL ---
    stopwords_pt = {
        "mídia", "oculta", "mensagem", "editada", "omitida", "áudio", "figurinha", "foto", "vídeo",
        "q", "n", "nn", "ta", "tá", "to", "tô", "tbm", "tb", "vc", "vcs", "pq", "oq", "gnt", "agr",
        "hj", "c", "né", "ne", "eh", "ai", "aí", "ia", "lá", "dps", "mds", "ir", "ah",
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "não", "nao", "uma", "os",
        "no", "se", "na", "por", "mais", "as", "dos", "das", "já", "ja", "eu", "você", "ele", "ela",
        "mas", "pra", "tipo", "vai", "tem", "foi", "aqui", "vou", "com", "me", "meu", "minha", "te", "seu",
        "seia", "isso", "esse", "essa", "tudo", "todo", "toda", "todos", "nada", "bem", "como",
        "só", "so", "ser", "ter", "era", "até", "mim", "mesmo", "quando", "onde", "quem", "coisa",
        "acho", "tenho", "tava", "tinha", "deu", "mano", "cara", "vamo", "vamos", "nossa",
        "ou", "nem", "sim", "fsi", "pdi"
    }

    # Processamento textual unificado (Elimina marcações @, caracteres ocultos e resíduos)
    mensagens_limpas_lista = []
    todas_palavras = []

    for msg in df['Mensagem'].astype(str):
        msg_min = msg.lower()
        msg_tratada = re.sub(r'@\w+', '', msg_min)
        msg_tratada = re.sub(r'[\u2066\u2067\u2068\u2069]', '', msg_tratada)
        msg_tratada = msg_tratada.replace('fsi', '').replace('pdi', '')

        # Guarda o texto para a nuvem de palavras
        mensagens_limpas_lista.append(msg_tratada)

        # Isola termos limpos para o ranking de palavras mais ditas
        msg_pontuacao_limpa = re.sub(r'[^\w\s]', '', msg_tratada)
        palavras = msg_pontuacao_limpa.split()
        palavras_filtradas = [p for p in palavras if p not in stopwords_pt and len(p) > 1]
        todas_palavras.extend(palavras_filtradas)

    # --- SEÇÃO 5: VISUALIZAÇÕES DE TEXTO (NUVEM E RANKING) ---
    st.header("🔤 O que mais se fala?")
    texto_completo_nuvem = " ".join(mensagens_limpas_lista)

    if len(texto_completo_nuvem.strip()) > 10:
        wordcloud = WordCloud(stopwords=stopwords_pt, background_color="white", width=800, height=350, max_words=80,
                              collocations=False).generate(texto_completo_nuvem)
        fig_wc, ax = plt.subplots(figsize=(10, 4))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig_wc)
    else:
        st.info("Texto insuficiente para gerar a Nuvem de Palavras para este filtro.")

    st.subheader("🗣️ Ranking de Palavras Mais Ditas")
    if todas_palavras:
        df_palavras = pd.DataFrame(todas_palavras, columns=['Palavra'])
        ranking_palavras = df_palavras['Palavra'].value_counts().reset_index()
        ranking_palavras.columns = ['Palavra', 'Repetições']

        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            fig_palavras = px.bar(ranking_palavras.head(20), x='Repetições', y='Palavra', orientation='h',
                                  color='Repetições', color_continuous_scale='Bluered',
                                  title="Termos mais frequentes na conversa")
            fig_palavras.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_palavras, use_container_width=True)
        with col_p2:
            st.dataframe(ranking_palavras.head(50), use_container_width=True, height=400)

    st.markdown("---")

    # --- SEÇÃO 6: PERFIL DE COMPORTAMENTO DOS PARTICIPANTES (TABS) ---
    st.header("🔬 Análises Comportamentais")

    tab_turnos, tab_vacuo, tab_risadas, tab_rede = st.tabs([
        "🕒 Preferência de Turno",
        "💀 Campeões do Vácuo",
        "😂 Classificador de Risadas",
        "🕸️ Mapa de Afinidade"
    ])

    # TAB 1: PREFERÊNCIA DE TURNO
    with tab_turnos:
        st.subheader("Em qual período do dia cada um mais interage?")
        turno_autor = df_completo.groupby(['Autor', 'Turno']).size().reset_index(name='Mensagens')
        fig_turno = px.bar(turno_autor, x='Mensagens', y='Autor', color='Turno', orientation='h', barmode='stack',
                           title="Distribuição de Mensagens por Turno",
                           color_discrete_map={'Madrugada 🦉': '#1F1F3A', 'Manhã ☕': '#FFD166', 'Tarde ☀️': '#06D6A0',
                                               'Noite 🌙': '#118AB2'})
        st.plotly_chart(fig_turno, use_container_width=True)

    # TAB 2: CAMPEÕES DO VÁCUO (QUEM É MAIS IGNORADO)
    with tab_vacuo:
        st.subheader("Quem é o integrante mais deixado no vácuo?")
        st.markdown(
            "*Definição: Mensagem enviada que encerra o chat por 2 horas ou mais antes de outra pessoa puxar assunto.*")

        limite_vacuo_horas = 2
        vacuos_por_autor = {autor: 0 for autor in df_completo['Autor'].unique()}
        total_mensagens_autor = df_completo['Autor'].value_counts().to_dict()

        for i in range(len(df_completo) - 1):
            autor_atual = df_completo.loc[i, 'Autor']
            tempo_atual = df_completo.loc[i, 'Data_Hora']
            proximo_tempo = df_completo.loc[i + 1, 'Data_Hora']

            diferenca_horas = (proximo_tempo - tempo_atual).total_seconds() / 3600
            if diferenca_horas >= limite_vacuo_horas:
                vacuos_por_autor[autor_atual] += 1

        dados_vacuo = []
        for autor, qtd_vacuos in vacuos_por_autor.items():
            total_msg = total_mensagens_autor.get(autor, 1)
            taxa_vacuo = (qtd_vacuos / total_msg) * 100
            dados_vacuo.append({"Autor": autor, "Vácuos Tomados": qtd_vacuos, "Taxa de Vácuo (%)": taxa_vacuo})

        df_vacuo = pd.DataFrame(dados_vacuo).sort_values(by="Taxa de Vácuo (%)", ascending=False)
        fig_vacuo = px.bar(df_vacuo, x='Taxa de Vácuo (%)', y='Autor', orientation='h',
                           title="% de Vácuos em Relação ao Total de Envios do Usuário",
                           hover_data=['Vácuos Tomados'], color='Taxa de Vácuo (%)', color_continuous_scale='Oranges')
        fig_vacuo.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_vacuo, use_container_width=True)

    # TAB 3: MAPEAMENTO DE RISADAS
    with tab_risadas:
        st.subheader("O Mapa do Riso (Estilos de Digitação)")


        def detectar_e_classificar_risada(msg):
            text = str(msg).lower()
            if re.search(r'k{3,}', text): return 'Tradicional (kkkk)'
            if re.search(r'(sk|ks){2,}', text): return 'Sinfonia de S (ksksks)'
            if re.search(r'(ja|ha|he){2,}', text): return 'Gringa (hahaha)'
            if re.search(r'(ka|ak){2,}', text): return 'Espalhafatosa (kakaka)'
            if re.search(r'(hu|uh){2,}', text): return 'Contida (huhuhu)'
            if re.search(r'([asdfghjkl]){6,}', text) and not re.search(r'[aeiou]{2,}',
                                                                       text): return 'Surto no Teclado (asdfg)'
            return None


        df_completo['Tipo_Risada'] = df_completo['Mensagem'].apply(detectar_e_classificar_risada)
        df_apenas_risadas = df_completo[df_completo['Tipo_Risada'].notna()]

        if not df_apenas_risadas.empty:
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                ranking_alegria = df_apenas_risadas['Autor'].value_counts().reset_index()
                ranking_alegria.columns = ['Autor', 'Quantidade de Risadas']
                fig_alegria = px.bar(ranking_alegria, x='Quantidade de Risadas', y='Autor', orientation='h',
                                     title="Quem mais ri no grupo?", color='Quantidade de Risadas',
                                     color_continuous_scale='Purples')
                fig_alegria.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_alegria, use_container_width=True)
            with col_r2:
                tipos_comuns = df_apenas_risadas['Tipo_Risada'].value_counts().reset_index()
                tipos_comuns.columns = ['Estilo', 'Frequência']
                fig_estilos = px.pie(tipos_comuns, values='Frequência', names='Estilo',
                                     title="Estilos de Risada Favoritos do Grupo", hole=0.4)
                st.plotly_chart(fig_estilos, use_container_width=True)

            st.markdown("**O Dialeto de cada Integrante (Matriz Cruzada)**")
            df_cruzado = pd.crosstab(df_apenas_risadas['Autor'], df_apenas_risadas['Tipo_Risada'])
            st.dataframe(df_cruzado, use_container_width=True)
        else:
            st.info("Nenhuma risada padrão foi identificada nas mensagens.")

    # TAB 4: MAPA DE AFINIDADE (REDE DE RESPOSTAS)
    with tab_rede:
        st.subheader("🗺️ Matriz de Proximidade (Quem responde quem?)")
        st.markdown(
            "*Lógica: Contabiliza interações sequenciais onde o participante B manda mensagem até 60 segundos após o participante A.*")

        lista_autores = list(i for i in df_completo['Autor'].unique() if i != "Rafa Cotuca")
        matriz_interacao = pd.DataFrame(0, index=lista_autores, columns=lista_autores)

        for i in range(len(df_completo) - 1):
            autor_A = df_completo.loc[i, 'Autor']
            tempo_A = df_completo.loc[i, 'Data_Hora']
            autor_B = df_completo.loc[i + 1, 'Autor']
            tempo_B = df_completo.loc[i + 1, 'Data_Hora']

            if autor_A == "Rafa Cotuca" or autor_B == "Rafa Cotuca":
                continue

            if autor_A != autor_B:
                diff_segundos = (tempo_B - tempo_A).total_seconds()
                if 0 <= diff_segundos <= 60:
                    matriz_interacao.loc[autor_A, autor_B] += 1

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=matriz_interacao.values, x=matriz_interacao.columns, y=matriz_interacao.index,
            colorscale='Viridis', text=matriz_interacao.values, texttemplate="%{text}", textfont={"size": 12}
        ))
        fig_heatmap.update_layout(
            title='Eixo Y (Quem iniciou) ➡️ Eixo X (Quem respondeu na sequência rápida)',
            xaxis_title="Quem respondeu logo após", yaxis_title="Quem mandou a primeira"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

else:
    st.warning("Nenhum dado pôde ser extraído. Verifique o formato do seu arquivo .txt.")