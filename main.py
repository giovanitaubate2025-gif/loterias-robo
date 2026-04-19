import requests

def acionar_robo_planilha():
    print("🚀 Iniciando o gatilho do Motor GG-456 via GitHub Actions...")
    
    # A URL NOVA QUE VOCÊ ACABOU DE GERAR NO APPS SCRIPT
    URL_DO_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycby-taEbqkJHCo7G0gNOXutIhk6IpTJ2TWmCyd8yoAJV0hKtGUV-wGYEuidJJg7OSFNDIA/exec"
    
    try:
        print(f"📡 Disparando a URL: {URL_DO_APPS_SCRIPT}?acao=EXECUTAR_TRATOR&loteria=TODOS")
        
        # Faz o chamado para a planilha via internet
        resposta = requests.get(f"{URL_DO_APPS_SCRIPT}?acao=EXECUTAR_TRATOR&loteria=TODOS")
        
        # Mostra no console do GitHub o que a planilha respondeu
        print("\n==============================================")
        print("📥 RESPOSTA DA PLANILHA:")
        print(resposta.text)
        print("==============================================\n")
        
        if resposta.status_code == 200:
            print("✅ Comunicação bem sucedida!")
        else:
            print(f"❌ O Google recusou a conexão. Código HTTP: {resposta.status_code}")
            
    except Exception as e:
        print(f"❌ Erro crítico ao tentar se conectar com a internet: {e}")

if __name__ == "__main__":
    acionar_robo_planilha()
