import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO ---
st.set_page_config(page_title="Consolidador de Extratos", layout="wide")
st.title("🕵️‍♀️ Ferramenta de Depuração de Lançamentos")
st.markdown("Faça o upload dos extratos para analisar a conversão dos dados.")


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
st.header("📤 1. Faça o Upload do Extrato CSV")
uploaded_file = st.file_uploader(
    "Arraste e solte o arquivo CSV aqui",
    type=['csv']
)


# --- 4. LÓGICA DE DEPURAÇÃO ---
if uploaded_file:
    # --- Leitura Controlada do CSV ---
    novos_nomes_colunas = [
        "DATA", "APLICACOES", "Valor_Principal_Resgatado", "Valor_Bruto_Resgatado", 
        "IOF_Retido", "IRRF_Retido", "Valor_Liquido_Resgatado", "Rendimento_Pago_Bruto",
        "Rendimento_Pago_Liquido", "Saldo_Principal", "POSICAO_Saldo_Bruto", "POSICAO_IOF",
        "POSICAO_IRRF", "POSICAO_Saldo_Liquido"
    ]
    try:
        df_origem = pd.read_csv(
            uploaded_file, sep=';', encoding='utf-8-sig', header=None,
            skiprows=9, skipfooter=3, engine='python'
        )
        df_origem = df_origem.iloc[:, :len(novos_nomes_colunas)]
        df_origem.columns = novos_nomes_colunas
        st.success("Arquivo lido e colunas renomeadas com sucesso!")

        # --- TELA DE DEPURAÇÃO ---
        st.header("🕵️‍♀️ 2. Análise da Limpeza de Dados")
        st.info("Vamos inspecionar o conteúdo das colunas de valor antes e depois da tentativa de limpeza.")

        colunas_para_inspecionar = [coluna_iof, coluna_irrf, coluna_rendimento]
        
        st.subheader("Dados Originais (como foram lidos do arquivo)")
        st.dataframe(df_origem[colunas_para_inspecionar].head(15))

        # ---- Aplica a limpeza em uma cópia para ver o resultado ----
        df_copia_debug = df_origem.copy()
        
        st.subheader("Dados Após a Tentativa de Limpeza e Conversão")
        
        for coluna in colunas_para_inspecionar:
            if coluna in df_copia_debug.columns:
                series_limpa = (
                    df_copia_debug[coluna].astype(str)
                    .str.replace('.', '', regex=False)    # Remove ponto de milhar
                    .str.replace(',', '.', regex=False)    # Troca vírgula por ponto
                    # Adicionando limpeza de R$ e espaços por segurança
                    .str.replace('R$', '', regex=False)
                    .str.strip()
                )
                # Cria uma nova coluna com o resultado da conversão para podermos comparar
                df_copia_debug[f'convertido_{coluna}'] = pd.to_numeric(series_limpa, errors='coerce')

        # Mostra apenas as colunas convertidas
        st.dataframe(df_copia_debug[[col for col in df_copia_debug.columns if 'convertido_' in col]].head(15))

        st.warning(
            "**Analise a tabela 'Dados Após a Tentativa de Limpeza' acima:**\n\n"
            "- Se os valores estiverem como **números** (ex: `7.92`, `0.08`), a limpeza está funcionando.\n"
            "- Se os valores estiverem como **NaN** (nulo), significa que a limpeza falhou. "
            "Isso indica que existe algum outro caractere inesperado no seu arquivo CSV."
        )

    except Exception as e:
        st.error(f"Ocorreu um erro durante a leitura ou depuração: {e}")
