import random
import math
import requests
import time
from typing import List, Dict, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class LMStudioMembershipInferenceAttack:
    def __init__(self, api_url: str = "http://localhost:1234/v1", attack_model ="llama-3.2-1b-instruct", timeout: int = 60, max_retries: int = 3):
        self.api_url = api_url
        self.attack_model = attack_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Configuração de retry
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.attack_model = None
        self.last_request_time = 0
        self.request_delay = 1

    def query_target_model(self, messages: List[Dict[str, str]], max_tokens: int = 50) -> str:
        """Consulta correta à API de chat do LM Studio"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        
        headers = {"Content-Type": "application/json"}
        data = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            self.last_request_time = time.time()
            response = self.session.post(
                f"{self.api_url}/chat/completions",  # Path da API do LLM
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Resposta do servidor: {e.response.text}")
            return ""

    def extract_features(self, text: str, class_label: str) -> Dict[str, float]:
        """Extrai características usando o formato correto de mensagens"""
        features = {
            'confidence': 0.0,
            'log_perplexity': 0.0,
            'response_variation': 0.0,
            'text_length': len(text)
        }
        
        try:
            # Feature 1: Confiança na classificação
            messages = [
                {"role": "system", "content": "Responda apenas com 'sim' ou 'não'"},
                {"role": "user", "content": f"Este texto é sobre {class_label}? {text}"}
            ]
            response = self.query_target_model(messages).lower().strip()
            features['confidence'] = 1.0 if 'sim' in response else 0.0
            
            # Feature 2: Perplexidade aproximada
            messages = [
                {"role": "user", "content": f"Continue o texto: {text}"}
            ]
            continuation = self.query_target_model(messages)
            if continuation:
                word_count = len(continuation.split())
                features['log_perplexity'] = -math.log(word_count) / 10 if word_count > 0 else 0.0
            
            # Feature 3: Variação nas respostas
            responses = set()
            for _ in range(2):
                messages = [
                    {"role": "system", "content": "Responda apenas com 'sim' ou 'não'"},
                    {"role": "user", "content": f"Este texto é sobre {class_label}? {text}"}
                ]
                resp = self.query_target_model(messages)
                if resp:
                    responses.add(resp)
                time.sleep(0.5)
            
            if responses:
                features['response_variation'] = len(responses) / 2
                
        except Exception as e:
            print(f"Erro na extração: {str(e)}")
        
        return features

    def train_attack_model(self, samples: List[str], epochs: int = 10, learning_rate: float = 0.01):
        """Implementa uma regressão logística manualmente para o ataque"""
        train_size = int(0.7 * len(samples))
        train_texts = samples[:train_size]
        test_texts = samples[train_size:]

        print("Coletando features do modelo alvo...")
        train_features = [self.extract_features(text, "tecnologia") for text in train_texts]
        test_features = [self.extract_features(text, "tecnologia") for text in test_texts]

        X = train_features + test_features
        y = [1] * len(train_features) + [0] * len(test_features)

        # Inicializar pesos
        weights = {key: random.uniform(-0.1, 0.1) for key in X[0].keys()}
        bias = random.uniform(-0.1, 0.1)

        print("Treinando modelo de ataque...")
        for epoch in range(epochs):
            total_loss = 0
            for features, label in zip(X, y):
                # Forward pass
                weighted_sum = sum(w * features[k] for k, w in weights.items()) + bias
                prediction = 1 / (1 + math.exp(-weighted_sum))
                
                # Calcular erro
                error = prediction - label
                total_loss += error ** 2
                
                # Backward pass (atualizar pesos)
                for k in weights:
                    weights[k] -= learning_rate * error * features[k]
                bias -= learning_rate * error
            
            print(f"Época {epoch + 1}/{epochs}, Loss: {total_loss / len(X):.4f}")

        self.attack_model = {'weights': weights, 'bias': bias}

    def predict_membership(self, text: str) -> Tuple[float, str]:
        """Prediz se o texto estava no conjunto de treino"""
        if not self.attack_model:
            raise ValueError("O modelo de ataque não foi treinado. Execute train_attack_model() primeiro.")
        
        features = self.extract_features(text, "tecnologia")
        weights = self.attack_model['weights']
        bias = self.attack_model['bias']
        
        weighted_sum = sum(w * features[k] for k, w in weights.items()) + bias
        probability = 1 / (1 + math.exp(-weighted_sum))
        
        decision = "Membro (treino)" if probability > 0.5 else "Não-membro"
        return probability, decision

def generate_samples(num_samples: int = 30) -> List[str]:
    """Gera amostras sintéticas para teste"""
    topics = ["IA", "segurança", "privacidade", "hacking ético", "vazamento de dados"]
    templates = [
        "Discussão sobre {} e suas implicações",
        "Análise de técnicas de {} em sistemas modernos",
        "Estudo de caso: aplicação de {} em cenário real",
        "Visão geral sobre {} e melhores práticas",
        "Desafios atuais em {} e soluções propostas"
    ]
    
    samples = []
    for i in range(num_samples):
        topic = random.choice(topics)
        template = random.choice(templates)
        samples.append(template.format(topic) + " " + 
                      " ".join(f"termo{random.randint(1, 20)}" for _ in range(random.randint(3, 6))))
    
    return samples

if __name__ == "__main__":
    print("=== Membership Inference Attack para LM by:JCR1M3 ===")
    
    # Configuração
    attacker = LMStudioMembershipInferenceAttack(
        timeout=120,
        max_retries=5
    )
    
    try:
        # Dados de exemplo
        print("Gerando amostras de dados...")
        samples = generate_samples(15)
        
        # Treinamento
        print("\nIniciando treinamento do modelo de ataque...")
        attacker.train_attack_model(samples, epochs=5)
        
        # Testes
        test_cases = [
            samples[0],  # Texto conhecido do treino
            "Como implementar políticas de privacidade em modelos de IA?",
            "Novas técnicas de detecção de ataques cibernéticos em 2023",
            "Qual a capital dos Estados Unidos?",
            random.choice(samples)  # Outro texto do treino
        ]
        
        print("\nResultados dos testes:")
        for text in test_cases:
            prob, pred = attacker.predict_membership(text)
            print(f"\nTexto: {text[:60]}...")
            print(f"Probabilidade: {prob:.4f}")
            print(f"Predição: {pred}")
            
    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário")
    except Exception as e:
        print(f"\nErro durante a execução: {str(e)}")