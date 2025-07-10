import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador de Extratos", layout="wide")
st.title("🤖 Aplicativo de Lançamentos de Aplicações Financeiras")
st.markdown("Faça o upload dos extratos (formato da imagem) para gerar os lançamentos contábeis.")


# --- 2. BARRA LATERAL PARA CONFIGURAÇÕES ---
st.sidebar.header("⚙️ 1. Nomes das Colunas no Arquivo")
st.sidebar.info(
    "Estes são os nomes padrão baseados na sua imagem. Ajuste apenas se o layout do arquivo mudar."
)

# Nomes das colunas extraídos da sua imagem. O '\n' representa a quebra de linha no cabeçalho.
coluna_data = st.sidebar.text_input("Coluna de Data", "DATA")
coluna_iof = st.sidebar.text_input("Coluna de IOF", "IOF\nRetido")
coluna_irrf = st.sidebar.text_input("Coluna de IRRF", "IRRF\nRetido")
coluna_rendimento = st.sidebar.text_input("Coluna de Rendimento", "Rendimento Pago\nBruto")


# --- 3. ÁREA DE UPLOAD DOS ARQUIVOS ---
st.header("📤 2. Faça o Upload dos Extratos")
uploaded_files = st.file_uploader(
    "Arraste e solte um ou mais arquivos (CSV ou Excel) aqui",
    accept_multiple_files=True,
    type=['csv', 'xlsx']
)


# --- 4. BOTÃO PARA PROCESSAR E LÓGICA DE TRANSFORMAÇÃO ---
if uploaded_files:
    if st.button("🚀 Gerar Lançamentos"):
        with st.spinner("Analisando extratos e aplicando regras..."):
            
            # --- Leitura e Concatenação ---
            lista_dfs = []
            for file in uploaded_files:
                try:
                    # Tenta ler como Excel, que é mais comum para esses relatórios
                    df = pd.read_excel(file)
                except Exception:
                    df = pd.read_csv(file, sep=';')
                lista_dfs.append(df)
            
            df_origem = pd.concat(lista_dfs, ignore_index=True)
            st.success("Arquivos lidos e unidos com sucesso!")

            # --- Limpeza Prévia ---
            # Remove linhas onde a data é nula, que geralmente são totais ou cabeçalhos
            df_origem.dropna(subset=[coluna_data], inplace=True)
            # Converte a coluna de data para o formato correto
            df_origem[coluna_data] = pd.to_datetime(df_origem[coluna_data], errors='coerce')


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
                if coluna_valor in df_origem.columns:
                    # Converte a coluna para numérico, tratando erros
                    df_origem[coluna_valor] = pd.to_numeric(df_origem[coluna_valor], errors='coerce')
                    
                    # Filtra apenas as linhas que têm valor válido (> 0) nesta coluna
                    df_temp = df_origem[df_origem[coluna_valor].fillna(0) > 0].copy()
                    
                    if not df_temp.empty:
                        st.write(f"✔️ Encontrados {len(df_temp)} lançamentos para {tipo}.")
                        
                        df_temp['Natureza'] = info['Natureza']
                        df_temp['Historico'] = info['Historico']
                        df_temp['Valor'] = df_temp[coluna_valor]

                        if info['Custo'] == 'debito':
                            df_temp['C. Custo debito'] = '2101020400'
                        else: # credito
                            df_temp['C. Custo credito'] = '2101020400'
                        
                        lancamentos_finais.append(df_temp)
                else:
                    st.warning(f"Aviso: A coluna '{coluna_valor}' não foi encontrada.")

            if not lancamentos_finais:
                st.warning("Nenhum lançamento de IOF, IRRF ou Rendimento foi encontrado nos arquivos.")
            else:
                df_final = pd.concat(lancamentos_finais, ignore_index=True)
                df_final.rename(columns={coluna_data: 'DT Movimento'}, inplace=True)
                
                # Define as colunas da tabela principal
                colunas_finais_obrigatorias = [
                    'FILIAL', 'DT Movimento', 'Numerario', 'Tipo', 'Valor', 'Natureza',
                    'Banco', 'Agencia', 'Conta Banco', 'Num Cheque', 'Historico',
                    'C. Custo debito', 'C. Custo credito', 'Item Debito', 'Item Credito',
                    'Cl Valor Deb', 'Cl Valor Crd'
                ]
                
                # Adiciona colunas que não existem no original, preenchendo com nulo
                for col in colunas_finais_obrigatorias:
                    if col not in df_final.columns:
                        df_final[col] = np.nan
                
                # Preenche os valores de Débito e Crédito com base na coluna 'Valor'
                df_final['Cl Valor Deb'] = np.where(df_final['C. Custo debito'].notna(), df_final['Valor'], np.nan)
                df_final['Cl Valor Crd'] = np.where(df_final['C. Custo credito'].notna(), df_final['Valor'], np.nan)

                # Salva o resultado no estado da sessão
                st.session_state['df_processado'] = df_final[colunas_finais_obrigatorias]
                st.balloons()
                st.success("Transformação concluída!")


# --- 5. EXIBIÇÃO DO RESULTADO E BOTÃO DE DOWNLOAD ---
if 'df_processado' in st.session_state:
    st.header("📊 3. Pré-visualização dos Lançamentos Gerados")
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
