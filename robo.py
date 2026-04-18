import requests
import json
import time
import urllib3

# Desativa avisos de segurança da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# O LINK DA SUA PLANILHA JÁ ESTÁ AQUI:
URL_PLANILHA = "https://script.google.com/macros/s/AKfycbzk15BvwYSZ4Js9PgMILNOzJdnkEyAyEzqC11Gq3N7G4B-td-YQLdyjuEnlMbdEFKTbPw/exec"

def perguntar_para_planilha():
    try:
        # Pergunta para a planilha qual é o último concurso que ela tem (via GET)
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

    return {
        "concurso": int(dados['numero']),
        "data": dados.get('dataApuracao', ''),
        "bolas": [str(n).zfill(2) for n in dados.get('listaDezenas', [])],
        "ganhadores": ganhadores
    }

def executar():
    print("🚜 INICIANDO O TRATOR DA LOTOFÁCIL...")
    
    # 1. Pergunta onde parou
    ultimo_planilha = perguntar_para_planilha()
    if ultimo_planilha == -1: return

    # 2. Vê onde a Caixa está
    dados_atuais = buscar_caixa()
    if not dados_atuais or 'numero' not in dados_atuais:
        print("⚠️ A Caixa não respondeu. Tentaremos depois.")
        return
        
    concurso_caixa = int(dados_atuais['numero'])
    print(f"📍 Caixa: {concurso_caixa} | 📊 Planilha: {ultimo_planilha}")

    if ultimo_planilha >= concurso_caixa:
        print("✅ A Planilha já está 100% atualizada!")
        return

    # 3. Baixa o que falta
    faltam = concurso_caixa - ultimo_planilha
    print(f"⬇️ Faltam {faltam} concursos. Iniciando o download...")
    
    lote = []
    # Loop do próximo concurso que a planilha precisa até o último da caixa
    for num in range(ultimo_planilha + 1, concurso_caixa + 1):
        # Se for o último, aproveita o que já baixamos lá em cima
        dados_brutos = buscar_caixa(num) if num != concurso_caixa else dados_atuais
        
        concurso_formatado = formatar_concurso(dados_brutos)
        if concurso_formatado:
            lote.append(concurso_formatado)
            
        # Quando o pacote tiver 50 resultados, manda pra planilha (ou se for o último que faltava)
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
            
            # Limpa o pacote para os próximos 50
            lote = []
            time.sleep(1) # Pausa pra não travar a caixa
            
        time.sleep(0.1) # Respira entre um download e outro

    print("\n🏁 TRABALHO CONCLUÍDO! A Planilha está atualizada.")

if __name__ == "__main__":
    executar()
