import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador de Extratos", layout="wide")
st.title("🤖 Aplicativo de Lançamentos de Aplicações Financeiras")
st.markdown("Faça o upload dos extratos para gerar os lançamentos contábeis.")

# --- 2. BARRA LATERAL PARA CONFIGURAÇÕES ---
st.sidebar.header("⚙️ 1. Nomes das Colunas no Arquivo")
st.sidebar.info("Ajuste os nomes abaixo para que correspondam aos cabeçalhos do seu arquivo.")
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

# --- 4. LÓGICA PRINCIPAL ---
if uploaded_files:
    # Lê os arquivos e une em um só
    lista_dfs = []
    for file in uploaded_files:
        try:
            # Tenta ler como Excel, pulando as 5 primeiras linhas
            df_temp = pd.read_excel(file, header=5)
            lista_dfs.append(df_temp)
        except Exception:
            file.seek(0) # Volta ao início do arquivo para a nova tentativa
            df_temp = pd.read_csv(file, sep=';', header=5)
            lista_dfs.append(df_temp)

    df_origem = pd.concat(lista_dfs, ignore_index=True)
    st.success(f"Arquivos lidos com sucesso! Total de {len(df_origem)} linhas encontradas.")

    # --- PASSO DE VERIFICAÇÃO (NOVO) ---
    st.subheader("🕵️‍♀️ Análise das Colunas Encontradas")
    st.info("Abaixo estão os nomes exatos das colunas que o Pandas encontrou no seu arquivo. Compare com os nomes configurados na barra lateral à esquerda.")
    st.code(df_origem.columns.tolist())
    # --- FIM DO PASSO DE VERIFICAÇÃO ---

    st.header("▶️ 3. Gerar Lançamentos")
    if st.button("🚀 Processar e Gerar Lançamentos"):
        
        # --- Validação de Coluna Essencial ---
        if coluna_data not in df_origem.columns:
            st.error(f"ERRO DE CONFIGURAÇÃO: A coluna de data '{coluna_data}' não foi encontrada no arquivo. As colunas disponíveis são: {df_origem.columns.tolist()}. Por favor, corrija o nome na barra lateral à esquerda e tente novamente.")
            st.stop() # Para a execução

        with st.spinner("Limpando e transformando os dados..."):
            # Limpeza Prévia
            df_origem.dropna(subset=[coluna_data], inplace=True)
            df_origem[coluna_data] = pd.to_datetime(df_origem[coluna_data], errors='coerce')
            
            # (O resto da sua lógica de transformação permanece aqui...)
            lancamentos_finais = []
            regras = {
                'IOF': {'coluna': coluna_iof, 'Natureza': '500513', 'Historico': 'IOF S/ RENDIMENTO', 'Custo': 'debito'},
                'IRRF': {'coluna': coluna_irrf, 'Natureza': '700721', 'Historico': 'IR S/ RENDIMENTO', 'Custo': 'debito'},
                'RENDIMENTO': {'coluna': coluna_rendimento, 'Natureza': '700713', 'Historico': 'REND S/ APLICAÇAO', 'Custo': 'credito'}
            }
            
            for tipo, info in regras.items():
                coluna_valor = info['coluna']
                if coluna_valor in df_origem.columns:
                    df_origem[coluna_valor] = pd.to_numeric(df_origem[coluna_valor], errors='coerce')
                    df_temp = df_origem[df_origem[coluna_valor].fillna(0) > 0].copy()
                    
                    if not df_temp.empty:
                        df_temp['Natureza'] = info['Natureza']
                        df_temp['Historico'] = info['Historico']
                        df_temp['Valor'] = df_temp[coluna_valor]

                        if info['Custo'] == 'debito': df_temp['C. Custo debito'] = '2101020400'
                        else: df_temp['C. Custo credito'] = '2101020400'
                        
                        lancamentos_finais.append(df_temp)

            if lancamentos_finais:
                df_final = pd.concat(lancamentos_finais, ignore_index=True)
                df_final.rename(columns={coluna_data: 'DT Movimento'}, inplace=True)
                
                colunas_finais_obrigatorias = [
                    'FILIAL', 'DT Movimento', 'Numerario', 'Tipo', 'Valor', 'Natureza',
                    'Banco', 'Agencia', 'Conta Banco', 'Num Cheque', 'Historico',
                    'C. Custo debito', 'C. Custo credito', 'Item Debito', 'Item Credito',
                    'Cl Valor Deb', 'Cl Valor Crd'
                ]
                for col in colunas_finais_obrigatorias:
                    if col not in df_final.columns: df_final[col] = np.nan
                
                df_final['Cl Valor Deb'] = np.where(df_final['C. Custo debito'].notna(), df_final['Valor'], np.nan)
                df_final['Cl Valor Crd'] = np.where(df_final['C. Custo credito'].notna(), df_final['Valor'], np.nan)

                st.session_state['df_processado'] = df_final[colunas_finais_obrigatorias]
                st.success("Transformação concluída!")
            else:
                st.warning("Nenhum lançamento de IOF, IRRF ou Rendimento foi encontrado.")

# --- 5. EXIBIÇÃO DO RESULTADO E BOTÃO DE DOWNLOAD ---
if 'df_processado' in st.session_state:
    st.header("📊 4. Pré-visualização dos Lançamentos Gerados")
    df_resultado = st.session_state['df_processado']
    st.write(f"Total de {len(df_resultado)} lançamentos gerados.")
    st.dataframe(df_resultado)

    @st.cache_data
    def converter_df_para_csv(df):
        return df.to_csv(index=False, sep=';', date_format='%d/%m/%Y').encode('utf-8')

    csv = converter_df_para_csv(df_resultado)
    st.download_button("📥 Baixar CSV Consolidado", csv, 'lancamentos_consolidados.csv', 'text/csv')
