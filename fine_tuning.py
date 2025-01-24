import openai
import yaml
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments

# Load your OpenAI API key
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
openai.api_key = config['openai_api_key']

# Load YAML file
with open('tuning.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Function to get response from ChatGPT-4 API
def get_response(prompt):
    response = openai.Completion.create(
        engine="gpt-4",  # Specify the engine
        prompt=prompt,
        max_tokens=150  # Adjust as needed
    )
    return response.choices[0].text.strip()

# Iterate over your data and get responses
for item in data:
    input_text = item["input"]
    output_text = get_response(input_text)
    print(f"Input: {input_text}\nOutput: {output_text}\n")

# 예시 데이터 변환
train_data = [{"input": item["input"], "output": item["output"]} for item in data]

# Dataset 객체로 변환
dataset = Dataset.from_dict({
    "input": [item["input"] for item in train_data], 
    "output": [item["output"] for item in train_data]
})

# 모델과 토크나이저 로드
model_name = "gpt-4"  # 예시: GPT-2 모델
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def tokenize_function(examples):
    # 입력과 출력을 하나의 문자열로 합쳐서 처리
    return tokenizer(examples["input"], padding="max_length", truncation=True, max_length=512)

# 데이터셋을 토큰화
tokenized_datasets = dataset.map(tokenize_function, batched=True)

# 훈련 인자 설정
training_args = TrainingArguments(
    output_dir='./results',          # 결과가 저장될 디렉터리
    evaluation_strategy="epoch",     # 평가 주기
    learning_rate=2e-5,              # 학습률
    per_device_train_batch_size=8,   # 배치 크기
    num_train_epochs=3,              # 학습 에폭 수
    weight_decay=0.01,               # 가중치 감소
)

# 평가 데이터셋 설정 (예: train 데이터와 동일)
eval_dataset = tokenized_datasets  # 필요한 경우 별도의 평가 데이터셋을 사용

trainer = Trainer(
    model=model,                         # 파인 튜닝할 모델
    args=training_args,                  # 학습 설정
    train_dataset=tokenized_datasets,    # 학습 데이터셋
    eval_dataset=eval_dataset           # 평가 데이터셋
)

# 훈련
trainer.train()

# 모델 저장
model.save_pretrained("./templar")
tokenizer.save_pretrained("./templar")

# 평가
trainer.evaluate()
