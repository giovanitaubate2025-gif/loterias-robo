import os
import json
import requests
from google.oauth2 import service_account

# 1. PEGA O JSON DE FORMA SEGURA DO COFRE DO GITHUB (SECRETS)
credenciais_json = os.environ.get("GOOGLE_CREDENTIALS")

def autenticar_google():
    if not credenciais_json:
        print("⚠️ ERRO: JSON não encontrado! Você esqueceu de cadastrar o GOOGLE_CREDENTIALS no GitHub Secrets.")
        return None
        
    print("🔄 Puxando a chave do Cofre Invisível e autenticando...")
    try:
        # Transforma o texto do cofre em um objeto JSON de verdade
        info_json = json.loads(credenciais_json)
        credenciais = service_account.Credentials.from_service_account_info(
            info_json, scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        print("✅ Autenticação com o Google Cloud aprovada!")
        return credenciais
    except Exception as e:
        print(f"❌ Erro ao ler a chave do cofre: {e}")
        return None

# 2. CHAMADA PARA O CÉREBRO DA PLANILHA (APPS SCRIPT)
def acionar_robo_planilha():
    print("🚀 Disparando o Trator GG-456 que está dentro do Google Sheets...")
    
    # IMPORTANTE: Coloque aqui a URL do seu App Script publicado (termina com /exec)
    URL_DO_APPS_SCRIPT = "COLOQUE_SUA_URL_DO_APPS_SCRIPT_AQUI"
    
    if URL_DO_APPS_SCRIPT == "COLOQUE_SUA_URL_DO_APPS_SCRIPT_AQUI":
        print("⚠️ ALERTA: Você precisa colar a URL gerada no botão 'Implantar' do Apps Script.")
        return

    # Manda o comando para o Apps Script executar a função 'EXECUTAR_TRATOR'
    try:
        resposta = requests.get(f"{URL_DO_APPS_SCRIPT}?acao=EXECUTAR_TRATOR&loteria=TODOS")
        print(f"✅ Resposta do Cérebro na Planilha: {resposta.text}")
    except Exception as e:
        print(f"❌ Erro ao chamar a planilha: {e}")

if __name__ == "__main__":
    autenticar_google()
    acionar_robo_planilha()
