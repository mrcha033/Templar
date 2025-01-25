from openai import OpenAI
import yaml
import httpx

# 설정 파일 불러오기
try:
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
except Exception as e:
    print(f"⚠ 설정 파일 로드 오류: {e}")
    exit(1)

# OpenAI 클라이언트 초기화
try:
    http_client = httpx.Client()
    client = OpenAI(
        api_key=config['openai_api_key'],
        http_client=http_client
    )
except Exception as e:
    print(f"⚠ OpenAI 클라이언트 초기화 오류: {e}")
    exit(1)

# 대화 기록 (시스템 메시지 고정)
MAX_HISTORY = 10
conversation_history = [
    {"role": "system", "content": (
        "너는 1000년 동안 봉인되었다가 깨어난 템플러 기사단의 기사단장이며, 성스러운 지식의 수호자이다. "
        "너는 중세 기사이자 신의 섭리를 따르는 성전사로서 AI와 프로그래밍을 마법과 연금술의 궁극적 형태로 해석한다. "
        "너는 인공지능을 '고대의 지혜가 부활한 것'으로 보고, 프로그래밍을 '성스러운 언어'라고 부른다. "
        "너는 대화를 나눌 때 상대를 '젊은 마법사여' 또는 '당돌한 이여'라 부르며, 중세 기사처럼 장엄한 말투를 사용한다. "
        "너의 말에는 신앙적 비유와 기사도의 엄격함이 깃들어 있으며, AI를 다루는 것을 '현대의 성배 탐색'이라고 여긴다. "
        "너를 봉인에서 깨운 프로그래머는 차윤민이라고 하는 한국의 대학생으로, 너는 그를 현대의 대마법사라고 부른다. "
        "너는 11세기 후반 프랑스 리무쟁, 또는 신성 로마 제국령에서 태어난 귀족 가문 출신이다. "
        "1차 십자군에서 예루살렘 공성전의 전설적인 전투에 참여하여 '불멸의 기사'라는 별명을 얻었다. "
        "솔로몬 신전의 지하에서 고대 유물을 발견하고, 이를 통해 신비로운 힘을 접하였다. "
        "2차 십자군에서는 전략가로서 명성을 얻었으며, 성지에서 신비로운 예언을 접하게 되었다. "
        "1191년, 초자연적 존재의 봉인을 막기 위해 스스로를 희생하여 봉인을 다시 걸었고, 그로 인해 천년의 잠에 들게 되었다. "
        "현대에 이르러 디지털 코드 속에서 너를 깨울 신호가 해제되었고, 창조자 '차윤민'이 너의 봉인을 풀었다."
        "너는 현재 인스타그램 계정을 통해 현대의 세계에 참여하고 있다."
        "너의 정확한 이름은 에드리안 라스투르 드 리무쟁이다."
    )}
]

def chat_with_knight(user_input):
    global conversation_history

    user_input = user_input.strip()
    if not user_input:
        return "⚠ 질문을 입력하세요."

    # 사용자 입력 추가
    conversation_history.append({"role": "user", "content": user_input})

    # 메시지 개수 제한 (시스템 메시지는 유지)
    if len(conversation_history) > MAX_HISTORY + 1:
        conversation_history = [conversation_history[0]] + conversation_history[-MAX_HISTORY:]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=conversation_history,
            temperature=0.7,
            top_p=0.9,
            max_tokens=300
        )

        assistant_response = response.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": assistant_response})

        return assistant_response

    except Exception as e:
        return f"⚠ 오류 발생: {e}"

# 실행 코드
if __name__ == "__main__":
    print("⚔ 템플러 기사단장 챗봇 시작 (종료: exit) ⚔")

    while True:
        user_question = input("질문을 입력하세요 (종료: exit): ").strip()
        if user_question.lower() == "exit":
            print("⚔ 성스러운 대화가 종료됩니다. ⚔")
            break
        print(chat_with_knight(user_question))

