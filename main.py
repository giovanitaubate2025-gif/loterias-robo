import pandas as pd
import requests
import os

# =========================================================================
# IMPORTADOR GG-456 (VERSÃO PARA CELULAR ANDROID)
# Lê planilhas do armazenamento do celular e envia para a nuvem.
# =========================================================================

URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

MAPA_PASTAS = {
    'Mega-Sena': 'MEGA-SENA',
    'Lotofácil': 'LOTOFÁCIL',
    'Quina': 'QUINA',
    'Lotomania': 'LOTOMANIA',
    'Timemania': 'TIMEMANIA',
    '+Milionária': 'MAISMILIONÁRIA',
    'Dia de Sorte': 'DIA_DE_SORTE',
    'Dupla Sena': 'DUPLA_SENA',
    'Super Sete': 'SUPER_SETE',
    'Loteca': 'LOTECA',
    'Federal': 'FEDERAL'
}

def enviar_lote(pasta_jogo, dados_lote):
    url = f"{URL_FIREBASE}HISTORICOS_DE_SORTEIOS/{pasta_jogo}.json?auth={SECRET_FIREBASE}"
    try:
        res = requests.patch(url, json=dados_lote, timeout=120)
        return res.status_code == 200
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return False

def limpar_dinheiro(valor):
    if pd.isna(valor): return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    try:
        texto = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(texto)
    except:
        return 0.0

def limpar_data(valor):
    if pd.isna(valor): return ""
    return str(valor)[:10].strip()

def procurar_pasta():
    print("==================================================")
    print("🔍 BUSCADOR DE PLANILHAS (ANDROID)")
    print("==================================================")
    
    # Caminhos comuns no Android
    caminhos_comuns = [
        '/storage/emulated/0/Download',
        '/storage/emulated/0/Planilha',
        '/storage/emulated/0/Download/Planilha',
        '.'
    ]
    
    for caminho in caminhos_comuns:
        try:
            arquivos = [f for f in os.listdir(caminho) if f.endswith('.xlsx') and not f.startswith('~')]
            if arquivos:
                print(f"✅ Planilhas encontradas na pasta: {caminho}")
                return caminho, arquivos
        except:
            continue
            
    # Se não achou automático, pede para o usuário digitar
    print("❌ Não achei as planilhas automaticamente.")
    print("No seu print, parece estar em Cartão SD > Planilha.")
    caminho_manual = input("Digite o caminho exato da pasta (ex: /storage/emulated/0/Planilha): ")
    
    try:
        arquivos = [f for f in os.listdir(caminho_manual) if f.endswith('.xlsx') and not f.startswith('~')]
        if arquivos:
            return caminho_manual, arquivos
    except Exception as e:
        print(f"Erro ao acessar a pasta: {e}")
        
    return None, []

def executar_importacao():
    caminho_base, arquivos = procurar_pasta()
    
    if not arquivos:
        print("Nenhuma planilha .xlsx foi encontrada para importar.")
        return
        
    print(f"\n🚀 INICIANDO IMPORTAÇÃO DE {len(arquivos)} ARQUIVOS...")

    for arquivo in arquivos:
        nome_puro = arquivo.split('(')[0].replace('.xlsx', '').strip()
        
        if nome_puro in MAPA_PASTAS:
            pasta_destino = MAPA_PASTAS[nome_puro]
            caminho_completo = os.path.join(caminho_base, arquivo)
            
            print(f"\n📊 Lendo: {arquivo} -> Destino: HISTORICOS_DE_SORTEIOS/{pasta_destino}")
            
            try:
                df = pd.read_excel(caminho_completo)
                coluna_concurso = df.columns[0]
                df = df.dropna(subset=[coluna_concurso])
                
                pacote_concursos = {}
                
                for _, linha in df.iterrows():
                    try:
                        concurso_str = str(int(linha[coluna_concurso]))
                    except ValueError:
                        continue 

                    # 1. DEZENAS
                    dezenas = []
                    for col in df.columns:
                        col_l = str(col).lower()
                        if 'bola' in col_l or 'd' in col_l or col_l.isdigit():
                            val = linha[col]
                            if pd.notna(val) and str(val).replace('.0','').isdigit():
                                dezenas.append(int(val))
                    
                    # 2. RATEIO
                    rateios = []
                    for col in df.columns:
                        col_l = str(col).lower()
                        if any(palavra in col_l for palavra in ['valor', 'premio', 'rateio', 'pago']):
                            rateios.append({
                                "faixa": str(col),
                                "valor": limpar_dinheiro(linha[col])
                            })
                    
                    # 3. ESPECIAL
                    especial = ""
                    for col in df.columns:
                        col_l = str(col).lower()
                        if any(palavra in col_l for palavra in ['time', 'coracao', 'trevo', 'mês', 'mes']):
                            if pd.notna(linha[col]):
                                especial = str(linha[col])

                    # 4. ACUMULOU
                    acumulou = "NÃO"
                    for col in df.columns:
                        if 'acumulad' in str(col).lower():
                            if pd.notna(linha[col]) and "sim" in str(linha[col]).lower():
                                acumulou = "SIM"
                    
                    pacote_concursos[concurso_str] = {
                        "data": limpar_data(linha.get('Data', linha.get('Data Sorteio', ""))),
                        "dezenas": dezenas,
                        "rateio": rateios,
                        "especial": especial,
                        "acumulou": acumulou
                    }

                print(f"Subindo {len(pacote_concursos)} concursos. Aguarde...")
                
                if enviar_lote(pasta_destino, pacote_concursos):
                    print(f"✅ SUCESSO! {pasta_destino} atualizada.")
                else:
                    print(f"❌ ERRO: Falha ao subir {pasta_destino}.")

            except Exception as e:
                print(f"❌ Erro crítico ao ler a planilha {arquivo}: {e}")

    print("\n🎉 IMPORTAÇÃO GERAL CONCLUÍDA! Seu Firebase está abastecido.")

if __name__ == "__main__":
    executar_importacao()
