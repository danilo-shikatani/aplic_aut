import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador Financeiro", layout="wide")
st.title("🤖 Aplicativo de Transformação de Lançamentos Financeiros")
st.markdown("Faça o upload dos extratos dos bancos para consolidar e criar os lançamentos para a tabela principal.")


# --- 2. BARRA LATERAL PARA CONFIGURAÇÕES ---
st.sidebar.header("⚙️ 1. Configuração das Colunas")
st.sidebar.info(
    "Ajuste os nomes abaixo para que correspondam exatamente "
    "aos cabeçalhos das colunas nos seus arquivos de origem."
)

# Usamos valores padrão para facilitar, mas o usuário pode alterar na tela
coluna_descricao = st.sidebar.text_input("Nome da coluna com a descrição (IOF, IRRF, etc.)", "Histórico")
coluna_valor = st.sidebar.text_input("Nome da coluna com os valores", "Valor Lançamento")
coluna_data = st.sidebar.text_input("Nome da coluna de data do movimento", "Data")


# --- 3. ÁREA DE UPLOAD DOS ARQUIVOS ---
st.header("📤 2. Upload dos Arquivos dos Bancos")
uploaded_files = st.file_uploader(
    "Arraste e solte os 3 arquivos (CSV ou Excel) aqui",
    accept_multiple_files=True,
    type=['csv', 'xlsx']
)


# --- 4. BOTÃO PARA PROCESSAR E LÓGICA DE TRANSFORMAÇÃO ---
if uploaded_files:
    st.info(f"{len(uploaded_files)} arquivo(s) carregado(s). Clique no botão abaixo para iniciar a transformação.")

    if st.button("🚀 Processar Arquivos"):
        with st.spinner("Mágica em andamento... Lendo e transformando os dados..."):
            
            # --- Lógica de Leitura e Concatenação ---
            lista_dfs = []
            for file in uploaded_files:
                try:
                    # Tenta ler como CSV, depois como Excel se falhar
                    try:
                        df = pd.read_csv(file, sep=';')
                    except Exception:
                        df = pd.read_excel(file)
                    lista_dfs.append(df)
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo {file.name}: {e}")
            
            if not lista_dfs:
                st.error("Nenhum arquivo pôde ser lido. Verifique o formato.")
            else:
                df_origem = pd.concat(lista_dfs, ignore_index=True)
                st.success("Arquivos lidos e unidos com sucesso!")

                # --- Lógica de Transformação (a mesma do script anterior) ---
                df_origem[coluna_descricao] = df_origem[coluna_descricao].astype(str)

                # Filtra cada tipo de lançamento
                df_iof = df_origem[df_origem[coluna_descricao].str.contains('IOF', case=False, na=False)].copy()
                df_irrf = df_origem[df_origem[coluna_descricao].str.contains('IRRF|I.R.', case=False, na=False)].copy()
                df_rendimento = df_origem[df_origem[coluna_descricao].str.contains('RENDIMENTO|APLICACAO', case=False, na=False)].copy()

                # Dicionário de regras
                REGRAS = {
                    'IOF': {'df': df_iof, 'Natureza': '500513', 'Historico': 'IOF S/ RENDIMENTO', 'Custo': 'debito'},
                    'IRRF': {'df': df_irrf, 'Natureza': '700721', 'Historico': 'IR S/ RENDIMENTO', 'Custo': 'debito'},
                    'RENDIMENTO': {'df': df_rendimento, 'Natureza': '700713', 'Historico': 'REND S/ APLICAÇAO', 'Custo': 'credito'}
                }

                lancamentos_processados = []

                for tipo, info in REGRAS.items():
                    df_temp = info['df']
                    if not df_temp.empty:
                        st.write(f"✔️ Encontrados {len(df_temp)} lançamentos de {tipo}.")
                        df_temp['Natureza'] = info['Natureza']
                        df_temp['Historico'] = info['Historico']
                        if info['Custo'] == 'debito':
                            df_temp['C. Custo debito'] = '2101020400'
                            df_temp['C. Custo credito'] = np.nan
                            df_temp['Cl Valor Deb'] = df_temp[coluna_valor]
                            df_temp['Cl Valor Crd'] = np.nan
                        else: # credito
                            df_temp['C. Custo debito'] = np.nan
                            df_temp['C. Custo credito'] = '2101020400'
                            df_temp['Cl Valor Deb'] = np.nan
                            df_temp['Cl Valor Crd'] = df_temp[coluna_valor]
                        lancamentos_processados.append(df_temp)
                
                if not lancamentos_processados:
                    st.warning("Nenhum lançamento de IOF, IRRF ou Rendimento foi encontrado nos arquivos.")
                else:
                    df_final = pd.concat(lancamentos_processados, ignore_index=True)
                    df_final.rename(columns={coluna_data: 'DT Movimento', coluna_valor: 'Valor'}, inplace=True)
                    df_final['DT Movimento'] = pd.to_datetime(df_final['DT Movimento'], dayfirst=True, errors='coerce')

                    # Garante que todas as colunas da tabela principal existam
                    colunas_finais_obrigatorias = [
                        'FILIAL', 'DT Movimento', 'Numerario', 'Tipo', 'Valor', 'Natureza',
                        'Banco', 'Agencia', 'Conta Banco', 'Num Cheque', 'Historico',
                        'C. Custo debito', 'C. Custo credito', 'Item Debito', 'Item Credito',
                        'Cl Valor Deb', 'Cl Valor Crd'
                    ]
                    for col in colunas_finais_obrigatorias:
                        if col not in df_final.columns:
                            df_final[col] = np.nan

                    # Salva o resultado no estado da sessão para ser usado pelo botão de download
                    st.session_state['df_processado'] = df_final[colunas_finais_obrigatorias]

                    st.balloons()
                    st.success("Transformação concluída com sucesso!")


# --- 5. EXIBIÇÃO DO RESULTADO E BOTÃO DE DOWNLOAD ---

# Verifica se o dataframe processado existe no estado da sessão
if 'df_processado' in st.session_state:
    st.header("📊 3. Resultado da Transformação")
    df_resultado = st.session_state['df_processado']
    st.write(f"Total de {len(df_resultado)} lançamentos gerados para a tabela principal.")
    st.dataframe(df_resultado)

    # Converte o dataframe para CSV em memória para o download
    @st.cache_data
    def converter_df_para_csv(df):
        return df.to_csv(index=False, sep=';', date_format='%d/%m/%Y').encode('utf-8')

    csv = converter_df_para_csv(df_resultado)

    st.download_button(
        label="📥 Baixar CSV Consolidado",
        data=csv,
        file_name='lancamentos_consolidados.csv',
        mime='text/csv',
    )