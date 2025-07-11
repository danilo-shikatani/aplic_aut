import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador de Extratos", layout="wide")
st.title("🤖 Aplicativo de Lançamentos de Aplicações Financeiras")
st.markdown("Faça o upload dos extratos em formato CSV para gerar os lançamentos contábeis.")

# --- 2. BARRA LATERAL PARA CONFIGURAÇÕES (Automático) ---
st.sidebar.header("⚙️ Nomes das Colunas em Análise")
coluna_data = "DATA"
coluna_iof = "IOF_Retido"
coluna_irrf = "IRRF_Retido"
coluna_rendimento = "Rendimento_Pago_Bruto"
st.sidebar.markdown(f"**Coluna de Data:** `{coluna_data}`")
st.sidebar.markdown(f"**Coluna de IOF:** `{coluna_iof}`")
st.sidebar.markdown(f"**Coluna de IRRF:** `{coluna_irrf}`")
st.sidebar.markdown(f"**Coluna de Rendimento:** `{coluna_rendimento}`")

# --- 3. ÁREA DE UPLOAD DOS ARQUIVOS ---
st.header("📤 2. Faça o Upload dos Extratos CSV")
uploaded_files = st.file_uploader(
    "Arraste e solte um ou mais arquivos CSV aqui",
    accept_multiple_files=True,
    type=['csv']
)

# --- 4. BOTÃO PARA PROCESSAR E LÓGICA DE TRANSFORMAÇÃO ---
if uploaded_files:
    if st.button("🚀 Gerar Lançamentos"):
        with st.spinner("Analisando extratos e aplicando regras..."):
            
            lista_dfs = []
            novos_nomes_colunas = [
                "DATA", "APLICACOES", "Valor_Principal_Resgatado", "Valor_Bruto_Resgatado", 
                "IOF_Retido", "IRRF_Retido", "Valor_Liquido_Resgatado", "Rendimento_Pago_Bruto",
                "Rendimento_Pago_Liquido", "Saldo_Principal", "POSICAO_Saldo_Bruto", "POSICAO_IOF",
                "POSICAO_IRRF", "POSICAO_Saldo_Liquido"
            ]

            for file in uploaded_files:
                try:
                    df_temp = pd.read_csv(
                        file, sep=';', encoding='utf-8-sig', header=None,
                        skiprows=9, skipfooter=3, engine='python'
                    )
                    
                    # --- CORREÇÃO PRINCIPAL (NOVA LINHA) ---
                    # Remove a primeira coluna, que está vazia por causa do ';' no início da linha
                    if not df_temp.empty:
                        df_temp = df_temp.drop(columns=df_temp.columns[0])
                    # --- FIM DA CORREÇÃO ---

                    df_temp = df_temp.iloc[:, :len(novos_nomes_colunas)]
                    df_temp.columns = novos_nomes_colunas
                    lista_dfs.append(df_temp)
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo {file.name}: {e}")

            if not lista_dfs:
                st.error("Nenhum arquivo pôde ser lido. Verifique o formato.")
                st.stop()

            df_origem = pd.concat(lista_dfs, ignore_index=True)
            st.success("Arquivos lidos e colunas alinhadas com sucesso!")

            # (O resto do código de transformação e geração de resultado continua o mesmo)
            df_origem.dropna(subset=[coluna_data], inplace=True)
            df_origem[coluna_data] = pd.to_datetime(df_origem[coluna_data], errors='coerce')

            lancamentos_finais = []
            regras = {
                'IOF': {'coluna': coluna_iof, 'Natureza': '500513', 'Historico': 'IOF S/ RENDIMENTO', 'Custo': 'debito'},
                'IRRF': {'coluna': coluna_irrf, 'Natureza': '700721', 'Historico': 'IR S/ RENDIMENTO', 'Custo': 'debito'},
                'RENDIMENTO': {'coluna': coluna_rendimento, 'Natureza': '700713', 'Historico': 'REND S/ APLICAÇAO', 'Custo': 'credito'}
            }
            
            for tipo, info in regras.items():
                coluna_valor_origem = info['coluna']
                if coluna_valor_origem in df_origem.columns:
                    df_origem[coluna_valor_origem] = df_origem[coluna_valor_origem].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_origem[coluna_valor_origem] = pd.to_numeric(df_origem[coluna_valor_origem], errors='coerce')
                    df_temp = df_origem[df_origem[coluna_valor_origem].fillna(0) > 0].copy()
                    
                    if not df_temp.empty:
                        st.write(f"✔️ Encontrados {len(df_temp)} lançamentos para {tipo}.")
                        df_temp['Natureza'] = info['Natureza']
                        df_temp['Historico'] = info['Historico']
                        df_temp['Valor'] = df_temp[coluna_valor_origem]
                        if info['Custo'] == 'debito':
                            df_temp['C. Custo debito'] = '2101020400'
                        else:
                            df_temp['C. Custo credito'] = '2101020400'
                        lancamentos_finais.append(df_temp)

            if lancamentos_finais:
                df_final = pd.concat(lancamentos_finais, ignore_index=True)
                df_final.rename(columns={coluna_data: 'DT Movimento'}, inplace=True)
                
                colunas_finais_obrigatorias = [
                    'FILIAL', 'DT Movimento', 'Numerario', 'Tipo', 'Valor', 'Natureza', 'Banco', 'Agencia', 
                    'Conta Banco', 'Num Cheque', 'Historico', 'C. Custo debito', 'C. Custo credito', 
                    'Item Debito', 'Item Credito', 'Cl Valor Deb', 'Cl Valor Crd'
                ]
                for col in colunas_finais_obrigatorias:
                    if col not in df_final.columns: df_final[col] = np.nan
                
                df_final['Cl Valor Deb'] = np.where(df_final['C. Custo debito'].notna(), df_final['Valor'], np.nan)
                df_final['Cl Valor Crd'] = np.where(df_final['C. Custo credito'].notna(), df_final['Valor'], np.nan)
                st.session_state['df_processado'] = df_final[colunas_finais_obrigatorias]
                st.balloons()
                st.success("Transformação concluída!")
            else:
                st.warning("Nenhum lançamento de IOF, IRRF ou Rendimento foi encontrado após a limpeza.")

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
    st.download_button("📥 Baixar CSV Consolidado", csv, 'lancamentos_consolidados.csv', 'text/csv')
