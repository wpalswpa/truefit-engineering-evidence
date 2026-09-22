# TrueFit — LLM 응답 검증 설계와 근거

운동 수업 계약서에서 쟁점을 뽑는 기능에서, **모델은 구간을 고르고 서버는 원문을 돌려줍니다.**
이 저장소는 그 설계와 검증 방법을 공개 가능한 범위에서 재현한 것입니다.

원본은 3인 팀 프로젝트(비공개)이고, 여기 있는 코드는 팀 코드의 사본이 아니라
검증 규칙만 최소 형태로 다시 쓴 것입니다. 범위는 [docs/architecture.md](docs/architecture.md).

## 바로 실행

```bash
git clone https://github.com/wpalswpa/truefit-engineering-evidence.git
cd truefit-engineering-evidence
python -m unittest discover -s tests -v
```

Python 3.10+. 표준 라이브러리만 쓰므로 **API 키도 네트워크도 필요 없습니다.**

## 무엇을 보면 되나

| 궁금한 것 | 파일 |
|---|---|
| LLM에 무엇을 맡기고 무엇을 안 맡겼나 | [docs/llm-boundary.md](docs/llm-boundary.md) |
| 왜 생성 대신 구간 선택인가 | [docs/decisions/001-source-span-extraction.md](docs/decisions/001-source-span-extraction.md) |
| 왜 저장 응답으로 회귀 검사하나 | [docs/decisions/002-offline-regression.md](docs/decisions/002-offline-regression.md) |
| 실제 입력과 출력 | [examples/](examples/) |
| 깨지면 안 되는 것 | [tests/test_contract_examples.py](tests/test_contract_examples.py) |
| 원본 프로젝트의 검증 기록 | [evidence/README.md](evidence/README.md) |

## 핵심 설계

```
계약 원문 ──▶ LLM 구간 선택 ──▶ 서버 응답 검증 ──▶ 원문 인용
  세그먼트      gpt-4.1-mini       스키마·ID 범위      서버가 직접 추출
  ID 부여       kind/first/last    잘못된 응답 거부    생성 문장 미사용
```

모델은 `{"kind": "...", "first": 3, "last": 3}` 만 돌려줍니다. 문장은 쓰지 않습니다.
인용문은 서버가 `source[start:end]` 로 만듭니다.

```python
rows.append({"quote": source[start:end], ...})   # 모델 응답이 아니라 원문에서
```

## 검사 이름이 곧 불변식입니다

```
quoted_text_is_reconstructed_from_source      인용문은 원문에서 만들어진다
model_generated_quote_is_never_rendered       모델이 쓴 문장은 화면에 가지 않는다
prompt_injection_text_cannot_reach_the_quote  주입 문구도 인용문을 조작하지 못한다
unknown_kind_is_rejected                      정의되지 않은 분류는 거부
out_of_range_segment_is_rejected              원문 범위 밖 구간은 거부
reversed_span_is_rejected                     first > last 는 범위가 아니다
partial_response_is_rejected                  필드가 빠지면 일부도 쓰지 않는다
extra_field_is_rejected                       모르는 필드가 붙으면 거부
boolean_is_not_accepted_as_segment_id         True 는 1 이지만 ID 가 아니다
```

## 이 설계가 막지 못하는 것

모델이 **존재하는 ID 중에서 틀린 구간**을 고르거나, 조건이 빠진 범위를 고르거나,
`kind` 를 잘못 분류하는 것은 그대로 남습니다. 원문에서 가져왔다는 사실과
올바른 근거를 골랐다는 사실은 다릅니다. 후자는 별도의 의미 검증이 필요하고,
아직 하지 않았습니다.

## 원본 프로젝트의 검증 기록

비공개 팀 저장소에서 2026-09-21에 기록된 결과입니다.
**이 공개 저장소가 재현하는 값이 아닙니다** — [evidence/](evidence/) 참고.

| 항목 | 기록 |
|---|---|
| pytest | 464 통과 · 실패 0 |
| 브라우저 여정 | 29 |
| 화면 검사 | 96 (화면폭 4종 × 24화면) |
| 재시작 · 백업 복원 | 통과 |
| AI 검토 | 저장 응답 11건 · 유료 호출 0건 |

실제 결제·송금, 실사용자 채택, 실제 계약에 대한 추출 정확도는 검증하지 않았습니다.

공개 시연: <https://truefit-wanted.onrender.com/>
(무료 호스팅이라 첫 접속이 느릴 수 있습니다.)
