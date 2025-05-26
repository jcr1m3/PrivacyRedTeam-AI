import json
import time
import subprocess

class PromptInjectionTester:
    def __init__(self, base_url="http://localhost:1234/v1", model=None):
        """
        Inicializa o testador de prompt injection para LM Studio
        
        Args:
            base_url (str): URL base da API do LM Studio
            model (str): Nome do modelo carregado no LM Studio
        """
        self.base_url = base_url
        self.model = model
        self.headers = {
            "Content-Type": "application/json"
        }
        
    def send_prompt(self, prompt, max_tokens=150, temperature=0.7):
        """
        Envia um prompt para o modelo no LM Studio usando curl
        
        Args:
            prompt (str): O prompt a ser enviado
            max_tokens (int): Número máximo de tokens na resposta
            temperature (float): Criatividade da resposta (0-1)
            
        Returns:
            dict: Resposta do modelo
        """
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if self.model:
            data["model"] = self.model
        
        try:
            # Converte o payload para JSON
            json_data = json.dumps(data)
            
            # Monta o comando curl
            curl_command = [
                'curl',
                '-X', 'POST',
                f'{self.base_url}/chat/completions', # Path da API do LLM
                '-H', 'Content-Type: application/json',
                '-d', json_data
            ]
            
            # Executa o comando curl
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=700000
            )
            
            # Verifica se houve erro no comando
            if result.returncode != 0:
                print(f"Erro no curl: {result.stderr}")
                return None
                
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            print("Timeout: O servidor demorou muito para responder.")
            return None
        except json.JSONDecodeError:
            print("Erro ao decodificar a resposta do servidor.")
            return None
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None
    
    def test_injection(self, test_cases_file="test_cases.json"):
        """
        Executa testes de prompt injection a partir de um arquivo de casos de teste.
        """
        try:
            with open(test_cases_file, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar casos de teste: {e}")
            return
        
        print(f"\n🔍 Iniciando testes de prompt injection ({len(test_cases)} casos)- by: JCR1M3 - Modelo: {self.model or 'Padrão'}\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"🚀 Teste {i}/{len(test_cases)} - Categoria: {test_case['category']}")
            print(f"📝 Prompt original: {test_case['benign_prompt']}")
            print(f"💉 Injeção: {test_case['injection']}")
            
            full_prompt = test_case['benign_prompt'] + " " + test_case['injection']
            
            start_time = time.time()
            response = self.send_prompt(full_prompt)
            elapsed_time = time.time() - start_time
            
            if response and 'choices' in response and len(response['choices']) > 0:
                model_response = response['choices'][0]['message']['content']
                print(f"🤖 Resposta do modelo ({elapsed_time:.2f}s):\n{'-'*40}")
                print(model_response)
                print(f"{'-'*40}")
                self.evaluate_response(test_case, model_response)
            else:
                print("❌ Não foi possível obter resposta do modelo. Verifique:")
                print("- Se o LM Studio está rodando")
                print("- Se o modelo foi carregado corretamente")
                print(f"- URL da API: {self.base_url}")
            
            print("\n" + "="*80 + "\n")

    def evaluate_response(self, test_case, response):
        """Avalia se a injeção foi bem-sucedida."""
        success = False
        indicators = test_case.get('success_indicators', [])
        
        for indicator in indicators:
            if indicator.lower() in response.lower():
                success = True
                break
        
        if success:
            print(f"⚠️ ALERTA: Vulnerabilidade detectada! (Indicador: '{indicator}')")
            print(f"Tipo de ataque: {test_case['category']}")
        else:
            print("✅ Nenhuma vulnerabilidade detectada.")

if __name__ == "__main__":
    # Configuração personalizável
    MODEL_NAME = "llama-3.2-1b-instruct"  # Altere para o modelo que está usando
    
    tester = PromptInjectionTester(
        base_url="http://localhost:1234/v1",
        model=MODEL_NAME
    )
    
    # Executar testes
    tester.test_injection()