import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador Financeiro", layout="wide")
st.title("🤖 Aplicativo de Criação de Lançamentos Financeiros")
st.markdown("Faça o upload dos extratos para gerar os lançamentos de IOF, IRRF e Rendimentos.")


# --- 2. BARRA LATERAL PARA CONFIGURAÇÕES ---
st.sidebar.header("⚙️ 1. Configuração das Colunas")
st.sidebar.info(
    "Ajuste os nomes abaixo para que correspondam exatamente "
    "aos cabeçalhos das colunas nos seus arquivos de origem."
)

# Novos campos para as colunas de valor específicas
coluna_iof = st.sidebar.text_input("Nome da coluna de IOF", "IOF")
coluna_irrf = st.sidebar.text_input("Nome da coluna de IRRF", "IRRF")
coluna_rendimento = st.sidebar.text_input("Nome da coluna de Rendimento", "Rendimento Bruto")
coluna_data = st.sidebar.text_input("Nome da coluna de data do movimento", "Data")


# --- 3. ÁREA DE UPLOAD DOS ARQUIVOS ---
st.header("📤 2. Upload dos Arquivos de Origem")
uploaded_files = st.file_uploader(
    "Arraste e solte os 3 arquivos (CSV ou Excel) aqui",
    accept_multiple_files=True,
    type=['csv', 'xlsx']
)


# --- 4. BOTÃO PARA PROCESSAR E NOVA LÓGICA DE TRANSFORMAÇÃO ---
if uploaded_files:
    if st.button("🚀 Gerar Lançamentos"):
        with st.spinner("Processando... Lendo arquivos e aplicando regras..."):
            
            # --- Lógica de Leitura e Concatenação ---
            lista_dfs = []
            for file in uploaded_files:
                try:
                    df = pd.read_csv(file, sep=';')
                except Exception:
                    df = pd.read_excel(file)
                lista_dfs.append(df)
            
            df_origem = pd.concat(lista_dfs, ignore_index=True)
            st.success("Arquivos lidos e unidos com sucesso!")

            # --- Lógica de Transformação por Coluna ---
            lancamentos_finais = []

            # Regras de Negócio
            regras = {
                'IOF': {'coluna': coluna_iof, 'Natureza': '500513', 'Historico': 'IOF S/ RENDIMENTO', 'Custo': 'debito'},
                'IRRF': {'coluna': coluna_irrf, 'Natureza': '700721', 'Historico': 'IR S/ RENDIMENTO', 'Custo': 'debito'},
                'RENDIMENTO': {'coluna': coluna_rendimento, 'Natureza': '700713', 'Historico': 'REND S/ APLICAÇAO', 'Custo': 'credito'}
            }
            
            for tipo, info in regras.items():
                coluna_valor = info['coluna']
                # Verifica se a coluna de valor existe no dataframe
                if coluna_valor in df_origem.columns:
                    # Filtra apenas as linhas que têm valor > 0 nesta coluna
                    df_temp = df_origem[pd.to_numeric(df_origem[coluna_valor], errors='coerce').fillna(0) > 0].copy()
                    
                    if not df_temp.empty:
                        st.write(f"✔️ Encontrados {len(df_temp)} lançamentos para {tipo}.")
                        
                        # Preenche as colunas com base nas regras
                        df_temp['Natureza'] = info['Natureza']
                        df_temp['Historico'] = info['Historico']
                        df_temp['Valor'] = pd.to_numeric(df_temp[coluna_valor], errors='coerce')

                        if info['Custo'] == 'debito':
                            df_temp['C. Custo debito'] = '2101020400'
                            df_temp['C. Custo credito'] = np.nan
                        else: # credito
                            df_temp['C. Custo debito'] = np.nan
                            df_temp['C. Custo credito'] = '2101020400'
                        
                        lancamentos_finais.append(df_temp)
                else:
                    st.warning(f"Aviso: A coluna '{coluna_valor}' não foi encontrada ou não possui valores válidos.")

            if not lancamentos_finais:
                st.warning("Nenhum lançamento de IOF, IRRF ou Rendimento foi encontrado nos arquivos com base nas colunas especificadas.")
            else:
                df_final = pd.concat(lancamentos_finais, ignore_index=True)
                df_final.rename(columns={coluna_data: 'DT Movimento'}, inplace=True)
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

                st.session_state['df_processado'] = df_final[colunas_finais_obrigatorias]
                st.balloons()
                st.success("Transformação concluída com sucesso!")


# --- 5. EXIBIÇÃO DO RESULTADO E BOTÃO DE DOWNLOAD ---
if 'df_processado' in st.session_state:
    st.header("📊 3. Resultado da Transformação")
    df_resultado = st.session_state['df_processado']
    st.write(f"Total de {len(df_resultado)} lançamentos gerados para a tabela principal.")
    st.dataframe(df_resultado)

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
