import streamlit as st
import pandas as pd
import numpy as np
import io
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador de Extratos", layout="wide")
st.title("🤖 Aplicativo de Lançamentos de Aplicações Financeiras")
st.markdown("Faça o upload dos extratos para gerar os lançamentos contábeis.")

# --- 2. BARRA LATERAL PARA CONFIGURAÇÕES ---
st.sidebar.header("⚙️ 1. Informações do Lançamento")
filial_input = st.sidebar.text_input("Nome da Filial", "CORPOREOS - SERVICOS 0001-98")
banco_input = st.sidebar.text_input("Nome do Banco", "BANCO ITAU")
st.sidebar.info("A Agência e a Conta serão extraídas automaticamente do arquivo.")

# Nomes das colunas que vamos procurar no arquivo
coluna_data = "DATA"
coluna_iof = "IOF_Retido"
coluna_irrf = "IRRF_Retido"
coluna_rendimento = "Rendimento_Pago_Bruto"

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
            
            lista_dfs_processados = []
            for file in uploaded_files:
                st.write(f"--- Processando arquivo: {file.name} ---")
                file.seek(0)
                content = file.getvalue().decode('utf-8')
                
                agencia_extraida = None
                conta_extraida = None
                for line in content.splitlines():
                    if "agência/conta:" in line.lower():
                        match = re.search(r'(\d+-\d+-\d+|\d+-\d+)', line)
                        if match:
                            partes = match.group(0).split('-')
                            agencia_extraida = partes[0]
                            conta_extraida = "".join(partes[1:])
                            st.write(f"✔️ Agência encontrada: **{agencia_extraida}** | Conta encontrada: **{conta_extraida}**")
                            break
                
                novos_nomes_colunas = [
                    "DATA", "APLICACOES", "Valor_Principal_Resgatado", "Valor_Bruto_Resgatado", 
                    "IOF_Retido", "IRRF_Retido", "Valor_Liquido_Resgatado", "Rendimento_Pago_Bruto",
                    "Rendimento_Pago_Liquido", "Saldo_Principal", "POSICAO_Saldo_Bruto", "POSICAO_IOF",
                    "POSICAO_IRRF", "POSICAO_Saldo_Liquido"
                ]
                
                data_io = io.StringIO(content)
                df_origem = pd.read_csv(
                    data_io, sep=';', encoding='utf-8-sig', header=None,
                    skiprows=9, skipfooter=3, engine='python'
                )
                df_origem = df_origem.drop(columns=df_origem.columns[0])
                df_origem = df_origem.iloc[:, :len(novos_nomes_colunas)]
                df_origem.columns = novos_nomes_colunas
                
                df_origem['FILIAL'] = filial_input
                df_origem['Banco'] = banco_input
                df_origem['Agencia'] = agencia_extraida
                df_origem['Conta Banco'] = conta_extraida
                lista_dfs_processados.append(df_origem)

            df_completo = pd.concat(lista_dfs_processados, ignore_index=True)
            st.success("Arquivos lidos e dados de cabeçalho extraídos com sucesso!")

            df_completo.dropna(subset=[coluna_data], inplace=True)
            df_completo[coluna_data] = pd.to_datetime(df_completo[coluna_data], errors='coerce')

            lancamentos_finais = []
            regras = {
                'IOF': {'coluna': coluna_iof, 'Natureza': '500513', 'Numerario': 'M1', 'Tipo': 'P', 'Historico': 'IOF S/ RENDIMENTO', 'Custo': 'debito'},
                'IRRF': {'coluna': coluna_irrf, 'Natureza': '700721', 'Numerario': 'M1', 'Tipo': 'P', 'Historico': 'IR S/ RENDIMENTO', 'Custo': 'debito'},
                'RENDIMENTO': {'coluna': coluna_rendimento, 'Natureza': '700713', 'Numerario': 'M1', 'Tipo': 'R' 'Historico': 'REND S/ APLICAÇAO', 'Custo': 'credito'}
            }
            
            for tipo, info in regras.items():
                coluna_valor_origem = info['coluna']
                if coluna_valor_origem in df_completo.columns:
                    df_completo[coluna_valor_origem] = df_completo[coluna_valor_origem].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_completo[coluna_valor_origem] = pd.to_numeric(df_completo[coluna_valor_origem], errors='coerce')
                    df_temp = df_completo[df_completo[coluna_valor_origem].fillna(0) > 0].copy()
                    
                    if not df_temp.empty:
                        df_temp['Natureza'] = info['Natureza']
                        df_temp['Historico'] = info['Historico']
                        df_temp['Numerario'] = info['Numerario']
                        df_temp['Tipo'] = info['Tipo']
                        df_temp['Valor'] = df_temp[coluna_valor_origem]
                        if info['Custo'] == 'debito':
                            df_temp['C. Custo debito'] = '2101020400'
                        else:
                            df_temp['C. Custo credito'] = '2101020400'
                        lancamentos_finais.append(df_temp)

            if not lancamentos_finais:
                st.warning("Nenhum lançamento de IOF, IRRF ou Rendimento foi encontrado nos arquivos.")
            else:
                df_final = pd.concat(lancamentos_finais, ignore_index=True)
                df_final.rename(columns={coluna_data: 'DT Movimento'}, inplace=True)
                
                colunas_finais_obrigatorias = [
                    'FILIAL', 'DT Movimento', 'Numerario', 'Tipo', 'Valor', 'Natureza', 'Banco', 'Agencia', 
                    'Conta Banco', 'Num Cheque', 'Historico', 'C. Custo debito', 'C. Custo credito', 
                    'Item Debito', 'Item Credito', 'Cl Valor Deb', 'Cl Valor Crd'
                ]
                for col in colunas_finais_obrigatorias:
                    if col not in df_final.columns: df_final[col] = np.nan
                
                # --- CORREÇÃO APLICADA AQUI ---
                # As duas linhas abaixo foram removidas (ou comentadas) para que as colunas fiquem vazias
                # df_final['Cl Valor Deb'] = np.where(df_final['C. Custo debito'].notna(), df_final['Valor'], np.nan)
                # df_final['Cl Valor Crd'] = np.where(df_final['C. Custo credito'].notna(), df_final['Valor'], np.nan)

                st.session_state['df_processado'] = df_final[colunas_finais_obrigatorias]
                st.balloons()
                st.success("Transformação concluída!")

# --- 5. EXIBIÇÃO DO RESULTADO E BOTÃO DE DOWNLOAD ---
if 'df_processado' in st.session_state:
    st.header("📊 3. Pré-visualização dos Lançamentos Gerados")
    df_resultado = st.session_state['df_processado']
    st.write(f"Total de {len(df_resultado)} lançamentos gerados.")
    st.dataframe(df_resultado)

    @st.cache_data
    def converter_df_para_csv(df):
        return df.to_csv(index=False, sep=';', date_format='%d/%m/%Y').encode('utf-8')
    csv = converter_df_para_csv(df_resultado)
    st.download_button("📥 Baixar CSV Consolidado", csv, 'lancamentos_consolidados.csv', 'text/csv')
