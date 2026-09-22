"""모델 응답을 제품 상태로 바꾸기 전에 서버가 통과시키는 관문.

비공개 팀 저장소의 검증 계층에서 **규칙만** 떼어 최소 형태로 다시 썼다.
팀 코드를 복사하지 않았고, 계약·정산·인증 로직은 포함하지 않는다.
여기 있는 것은 하나뿐이다 — 모델이 고른 결과를 서버가 어떻게 믿지 않는가.

설계 한 줄: **모델은 구간을 고르고, 서버는 원문을 돌려준다.**
모델이 쓴 문장은 사용자에게 보여 주는 인용문이 되지 않는다.
"""
from __future__ import annotations


class ValidationError(Exception):
    """모델 응답을 신뢰할 수 없을 때. 호출부는 원문 확인 경로로 안내한다."""


# 분류 가능한 쟁점. 모델은 이 목록 밖의 값을 만들 수 없다.
ISSUE_KINDS = {
    "schedule_agreement": "일정 변경 합의 주장",
    "not_received": "수업 미이용 주장",
    "wrong_deduction": "회차·금액 처리 이의",
    "other": "추가 확인이 필요한 설명",
}

# 모델에 요구하는 응답 스키마. 필드 세 개뿐이고 문장은 받지 않는다.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": sorted(ISSUE_KINDS)},
                    "first": {"type": "integer"},
                    "last": {"type": "integer"},
                },
                "required": ["kind", "first", "last"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["issues"],
    "additionalProperties": False,
}

MAX_ISSUES = 6


def split_segments(source: str) -> list[dict]:
    """원문을 문장 단위로 쪼개고 1부터 번호를 매긴다.

    모델에게는 이 번호만 보여 준다. 모델이 돌려주는 것도 번호뿐이다.
    """
    segments, start = [], 0
    for index, char in enumerate(source):
        if char in ".!?\n" or index == len(source) - 1:
            text = source[start:index + 1].strip()
            if text:
                segments.append({
                    "id": len(segments) + 1,
                    "start": source.index(text, start),
                    "end": source.index(text, start) + len(text),
                    "text": text,
                })
            start = index + 1
    return segments


def materialize(response: dict, source: str) -> list[dict]:
    """모델 응답을 화면에 올릴 수 있는 형태로 바꾼다. 통과하지 못하면 예외.

    인용문(`quote`)은 응답에서 가져오지 않는다. 항상 `source[start:end]` 로 만든다.
    그래서 모델이 무엇을 쓰든 인용문에 섞이지 않는다.
    """
    segments = split_segments(source)

    if not isinstance(response, dict) or set(response) != {"issues"}:
        raise ValidationError("응답 형식을 확인하지 못했습니다.")
    issues = response["issues"]
    if not isinstance(issues, list) or len(issues) > MAX_ISSUES:
        raise ValidationError("응답 항목 수를 확인하지 못했습니다.")

    rows = []
    for item in issues:
        # 키가 하나라도 빠지거나 더 붙으면 거부한다. 부분 응답을 받아들이지 않는다.
        if not isinstance(item, dict) or set(item) != {"kind", "first", "last"}:
            raise ValidationError("응답 항목의 형식을 확인하지 못했습니다.")

        kind, first, last = item["kind"], item["first"], item["last"]
        if kind not in ISSUE_KINDS:
            raise ValidationError("정의되지 않은 분류입니다.")
        # bool 은 int 의 하위형이라 isinstance 로는 걸러지지 않는다. type 으로 본다.
        if type(first) is not int or type(last) is not int:
            raise ValidationError("구간 번호가 정수가 아닙니다.")
        if not 1 <= first <= last <= len(segments):
            raise ValidationError("원문 범위를 벗어난 구간입니다.")

        start = segments[first - 1]["start"]
        end = segments[last - 1]["end"]
        rows.append({
            "kind": kind,
            "label": ISSUE_KINDS[kind],
            "quote": source[start:end],   # 모델의 문장이 아니라 원문에서 직접 추출
            "start": start,
            "end": end,
        })
    return rows
