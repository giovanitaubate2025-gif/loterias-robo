import requests
import json
import time
import urllib3

# Desativa avisos de segurança da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# O SEU NOVO LINK DA PLANILHA JÁ ESTÁ AQUI:
URL_PLANILHA = "https://script.google.com/macros/s/AKfycbw8pc9Dh-aVqNJ2KmycFAy3xyMj_2bshtDovNOVV-99CO8t5v_sY0IUbshu23Ysbl15xQ/exec"

def perguntar_para_planilha():
    try:
        res = requests.get(URL_PLANILHA, timeout=10)
        if res.status_code == 200:
            dados = res.json()
            return int(dados.get('ultimo', 0))
    except Exception as e:
        print(f"❌ Erro ao perguntar para a planilha: {e}")
    return -1

def buscar_caixa(concurso=""):
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{concurso}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def formatar_concurso(dados):
    if not dados or 'numero' not in dados: return None
    
    ganhadores = 0
    if dados.get('listaRateioPremio') and len(dados['listaRateioPremio']) > 0:
        ganhadores = dados['listaRateioPremio'][0].get('numeroDeGanhadores', 0)

    # CIRÚRGICO: Pega as dezenas brutas
    dezenas_brutas = dados.get('listaDezenas', [])
    
    # CIRÚRGICO: Converte para número inteiro para poder ordenar corretamente
    dezenas_numeros = [int(n) for n in dezenas_brutas if str(n).strip() != ""]
    
    # CIRÚRGICO: Ordena do menor para o maior (Crescente)
    dezenas_numeros.sort()
    
    # CIRÚRGICO: Transforma de volta em texto com 2 dígitos (ex: "5" vira "05")
    bolas_organizadas = [str(n).zfill(2) for n in dezenas_numeros]

    return {
        "concurso": int(dados['numero']),
        "data": dados.get('dataApuracao', ''),
        "bolas": bolas_organizadas, # Bolas 100% em ordem crescente
        "ganhadores": ganhadores
    }

def executar():
    print("🚜 INICIANDO O TRATOR CIRÚRGICO DA LOTOFÁCIL...")
    
    ultimo_planilha = perguntar_para_planilha()
    if ultimo_planilha == -1: return

    dados_atuais = buscar_caixa()
    if not dados_atuais or 'numero' not in dados_atuais:
        print("⚠️ A Caixa não respondeu. Tentaremos depois.")
        return
        
    concurso_caixa = int(dados_atuais['numero'])
    print(f"📍 Caixa: {concurso_caixa} | 📊 Planilha: {ultimo_planilha}")

    if ultimo_planilha >= concurso_caixa:
        print("✅ A Planilha já está 100% atualizada!")
        return

    faltam = concurso_caixa - ultimo_planilha
    print(f"⬇️ Faltam {faltam} concursos. Iniciando o download ordenado...")
    
    lote = []
    
    for num in range(ultimo_planilha + 1, concurso_caixa + 1):
        dados_brutos = buscar_caixa(num) if num != concurso_caixa else dados_atuais
        
        concurso_formatado = formatar_concurso(dados_brutos)
        if concurso_formatado:
            lote.append(concurso_formatado)
            
        # Envia em lotes de 50 para a planilha organizar e inserir
        if len(lote) == 50 or num == concurso_caixa:
            print(f"🚀 Enviando lote de {len(lote)} concursos para a Planilha...")
            try:
                res = requests.post(URL_PLANILHA, json={"lote": lote}, timeout=15)
                if "Sucesso" in res.text:
                    print(f"✅ Lote salvo! (Até o concurso {num})")
                else:
                    print(f"❌ Erro na planilha: {res.text}")
            except Exception as e:
                print(f"❌ Falha de conexão com a planilha ao enviar lote: {e}")
            
            lote = []
            time.sleep(1) 
            
        time.sleep(0.1)

    print("\n🏁 TRABALHO CONCLUÍDO! A Planilha está atualizada e organizada.")

if __name__ == "__main__":
    executar()
