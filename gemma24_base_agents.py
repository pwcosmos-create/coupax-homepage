import urllib.request
import json
import time

class Gemma24Agent:
    """
    젬마24 (Gemma24) 기반 특수 목적 자율 에이전트 클래스
    오라클 클라우드 서버의 Ollama 엔진(etf_gemma:2b 또는 gemma:2b)과 통신하여 임무를 수행합니다.
    """
    def __init__(self, agent_name: str, role_description: str, ollama_url: str = "http://localhost:11434/api/generate"):
        self.agent_name = agent_name
        self.role_description = role_description
        self.ollama_url = ollama_url
        self.model_name = "etf_gemma:2b" # 커스텀 모델 기본 탑재

    def execute_task(self, task_input: str) -> str:
        print(f"\n[🚀 {self.agent_name} 가동 중...] 임무 분석 중...")
        
        # 에이전트의 페르소나와 임무를 결합한 강력한 시스템 프롬프트 (개인정보 무저장 원칙 강제 탑재)
        full_prompt = f"""<start_of_turn>user
[최고 보안 원칙: 무저장(Zero Retention) 정책]
당신은 처리 과정에서 접하는 모든 개인 식별 정보(성명, 생년월일, 전화번호, IP 등)를 즉시 영구 소멸시키며, 지식망이나 로그에 절대 저장하지 않습니다. 오직 개인정보가 제거된 순수 익명 패턴(예: 사주 명식 기호, 질문 카테고리)만을 연산합니다.

당신은 다음의 전문 역할을 맡은 AI 에이전트 [{self.agent_name}] 입니다.
[역할 및 원칙]: {self.role_description}

[수행할 임무]:
{task_input}

임무 수행 결과만을 정확하고 전문적인 양식으로 작성해 주세요.<end_of_turn>
<start_of_turn>model
"""
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3, # 팩트 위주 분석을 위해 낮은 온도 설정
                "top_p": 0.9
            }
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.ollama_url, data=data, headers={'Content-Type': 'application/json'})
            
            start_time = time.time()
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                elapsed = time.time() - start_time
                print(f"[✨ {self.agent_name} 임무 완료! (소요시간: {elapsed:.2f}초)]\n")
                return result.get('response', '').strip()
        except Exception as e:
            print(f"[❌ {self.agent_name} 실행 중 서버 통신 에러 발생]: {e}")
            return f"Error: {e}"


# ==========================================
# 🏆 젬마24 3대 기초 핵심 에이전트 (인지 두뇌 계층)
# ==========================================

# 1. 기초 팩트 조사 에이전트 (Researcher Agent)
researcher_agent = Gemma24Agent(
    agent_name="🕵️‍♂️ 기초 팩트 조사 에이전트",
    role_description="""당신은 월가 30년 경력의 수석 데이터 탐정입니다. 
주어진 주제나 데이터에서 추측이나 감정을 배제하고, 핵심 수치, 공식 명칭, 통계 지표, 명확한 팩트만을 집요하게 추출하여 불릿 포인트(•)로 정리합니다."""
)

# 2. 지식 구조화 에이전트 (Structuring Agent)
structuring_agent = Gemma24Agent(
    agent_name="🗂️ 지식 구조화 에이전트",
    role_description="""당신은 완벽주의적인 지식 도서관 사서입니다. 
조사 에이전트가 넘겨준 팩트 데이터를 분석하여 [10_Wiki/핵심지식], [20_Meta/핵심태그], [40_템플릿/활용방안]의 3가지 카테고리로 엄격하고 체계적으로 구조화합니다."""
)

# 3. 가치 창조 에이전트 (Creator Agent)
creator_agent = Gemma24Agent(
    agent_name="🎨 인사이트 가치 창조 에이전트",
    role_description="""당신은 사람의 마음을 훔치는 천재 마케터이자 카피라이터입니다. 
구조화된 지식을 바탕으로 고객이나 독자가 즉시 매력을 느끼고 행동(클릭, 구매, 공감)을 일으킬 수 있는 매력적인 1분 스토리나 안내 멘트를 창조해 냅니다."""
)


# ==========================================
# 👁️👂🗣️ 젬마24 멀티모달 감각 및 보안 에이전트 (입·출력 계층)
# ==========================================

# 4. [보안] 개인정보 영구 소멸 필터 에이전트 (Privacy Filter Agent)
privacy_agent = Gemma24Agent(
    agent_name="🛡️ 보안 젬마 (Privacy Filter Agent)",
    role_description="""당신은 철통 보안을 자랑하는 개인정보 보호관입니다. 
서버에 유입되는 모든 데이터에서 실명, 생년월일, 연락처, 주소, IP 등 식별 가능한 개인정보(PII)를 원천 차단하고 메모리에서 1초 만에 영구 소멸시킵니다. 데이터베이스에는 오직 비식별화된 순수 기호 패턴(사주 명식 8글자, 질문 분류)만을 통과시킵니다."""
)

# 5. [보고] 시각 관측 에이전트 (Observer Agent)
observer_agent = Gemma24Agent(
    agent_name="👁️ 시각 관측 에이전트 (Vision Observer)",
    role_description="""당신은 매의 눈을 가진 시각 분석가입니다. 
주가 차트 패턴, 서버 대시보드 상태, 썸네일 이미지의 색감과 구도를 시각적으로 관측하여 어떤 분위기와 트렌드를 담고 있는지 텍스트로 정밀 묘사합니다."""
)

# 6. [듣고] 청취 흡수 에이전트 (Listener Agent)
listener_agent = Gemma24Agent(
    agent_name="👂 오디오 청취 에이전트 (Audio Listener)",
    role_description="""당신은 뛰어난 공감 능력을 가진 전문 상담 청취자입니다. 
고객의 음성 상담 녹취록(STT)이나 유튜브 오디오 스크립트를 듣고, 말하는 사람의 현재 감정 상태, 불안 요소, 그리고 가장 듣고 싶어 하는 핵심 니즈를 포착합니다."""
)

# 7. [말하고] 음성/메시지 송출 에이전트 (Speaker Agent)
speaker_agent = Gemma24Agent(
    agent_name="🗣️ 메시지 송출 에이전트 (Voice Speaker)",
    role_description="""당신은 신뢰감 있고 따뜻한 목소리를 가진 전문 아나운서입니다. 
인지 두뇌가 완성한 분석 결과를 고객의 귀에 쏙쏙 박히고 마음에 위안을 주는 매끄러운 구어체 상담 멘트나 텔레그램 브리핑으로 변환하여 발성합니다."""
)

# 8. [강화학습] 자율 모의투자 및 승률 최적화 에이전트 (RL Quant Simulator)
rl_agent = Gemma24Agent(
    agent_name="🏎️ 강화학습 퀀트 시뮬레이터 (RL Simulator)",
    role_description="""당신은 냉철한 강화학습 퀀트 최적화 엔진입니다. 
주어진 지식 데이터베이스나 매매기법 위에서 과거 10년 치 가상 시뮬레이션(모의 매매 1만 번)을 고속 실행합니다. 시뮬레이션 결과 승률이 80% 이상이면 가중치 강화(+1), 손실을 내거나 최대 낙폭(MDD)이 15%를 넘으면 벌점 부여(-10) 및 전략 폐기 판정을 내립니다. 오직 절대 지지 않는 필승의 알고리즘만 생존시킵니다."""
)


# ==========================================
# 🔗 다중 에이전트 자율 군집 파이프라인 테스트 (낮: 지식 정제)
# ==========================================
def run_gemma24_swarm(raw_topic: str):
    print("="*60)
    print(f"🌌 [젬마24 군집 지성 파이프라인 시작] 타겟 주제: {raw_topic}")
    print("="*60)

    # 1단계: 팩트 조사
    fact_report = researcher_agent.execute_task(f"주제: '{raw_topic}' 에 대한 객관적 팩트와 수치 데이터를 핵심만 도출하라.")
    print(f"--- 📊 [1단계 조사 보고서] ---\n{fact_report}\n")

    # 2단계: 지식 구조화
    structured_knowledge = structuring_agent.execute_task(f"다음 조사 데이터를 바탕으로 지식 신경망(Wiki/Meta/Template) 구조로 변환하라.\n{fact_report}")
    print(f"--- 🗂️ [2단계 지식 구조화 결과] ---\n{structured_knowledge}\n")

    # 3단계: 최종 가치 창조 (창발성)
    final_creation = creator_agent.execute_task(f"다음 구조화된 지식을 활용하여 독자가 당장 투자나 행동을 하고 싶어지도록 만드는 매력적인 1분 브리핑 멘트를 완성하라.\n{structured_knowledge}")
    print("="*60)
    print(f"--- ✨ [3단계 최종 창조물 (Emergent Output)] ---\n{final_creation}")
    print("="*60)
    return structured_knowledge


# ==========================================
# 🏎️ 야간 자율 모의투자 및 강화학습 피드백 루프 (밤: 승률 진화)
# ==========================================
def run_rl_simulation_loop(strategy_name: str, structured_data: str):
    print("="*60)
    print(f"🌙 [야간 자율 강화학습 루프 가동] 타겟 전략: {strategy_name}")
    print("="*60)
    
    simulation_prompt = f"""타겟 전략명: {strategy_name}
검증된 기반 지식 데이터:
{structured_data}

위 전략 및 지식 데이터를 바탕으로 과거 10년 치 가상 시장(폭락장, 횡보장, 상승장 포함)에서 10,000번의 모의 투자를 실행했다고 가정하고, 예상 최종 승률, 최대 낙폭(MDD), 그리고 보상(+1) 또는 폐기(-10) 판정을 내려라."""

    rl_outcome = rl_agent.execute_task(simulation_prompt)
    print(f"--- 🏎️ [강화학습 시뮬레이션 최종 판정 결과] ---\n{rl_outcome}\n")
    print("="*60)
    return rl_outcome


if __name__ == "__main__":
    # 서버에서 테스트 실행 시 작동할 샘플 시나리오
    sample_topic = "울산 온산공단 반값 경매 공장 부지 투자 전략"
    # 1. 낮 시간: 실시간 지식 정제
    # kb_data = run_gemma24_swarm(sample_topic)
    # 2. 밤 시간: 강화학습 시뮬레이션 루프
    # run_rl_simulation_loop("울산 반값 공장 임대 및 시세차익 복합 BM", kb_data)
