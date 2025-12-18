# PaperSearch - Claude Code 워크플로우 가이드

이 프로젝트는 Scopus API를 사용하여 학술 논문을 검색하고, AI 에이전트(Claude Code)가 검토하여 사용자 의도에 맞는 논문을 선별하는 시스템입니다.

## 환경 요구사항

- Python 3.10+
- `SCOPUS_API_KEY` 환경변수 설정 필요
- 의존성: `pip install -r requirements.txt`

## 프로젝트 구조

```
PaperSearch/
├── CLAUDE.md              # 이 파일 - Claude Code 워크플로우 정의
├── search_papers.py       # 논문 검색 CLI 스크립트
├── src/
│   ├── scopus_client.py   # Scopus API 클라이언트
│   ├── query_builder.py   # 검색 쿼리 빌더
│   └── paper_fetcher.py   # 논문 가져오기 및 저장
├── data/
│   └── papers/            # 검색 결과 저장 디렉토리
└── .claude/
    └── commands/          # 슬래시 커맨드 정의
```

## 슬래시 커맨드

### `/paper-search` - 논문 검색 및 선별

사용자가 `/paper-search` 커맨드를 실행하면 다음 워크플로우를 따릅니다.

---

## 논문 검색 워크플로우

사용자가 논문 검색을 요청하면 다음 단계를 순서대로 수행하세요:

### 1단계: 요구사항 수집

사용자에게 다음 정보를 질문하세요:

1. **연구 주제**: 어떤 주제의 논문을 찾고 있나요?
2. **검색 목적**: 논문을 찾는 구체적인 목적이 무엇인가요? (예: 최신 동향 파악, 특정 방법론 탐색, 선행연구 조사 등)
3. **논문 수**: 몇 편의 논문을 검토하길 원하나요? (기본값: 30편)
4. **연도 범위**: 특정 연도 범위가 있나요? (선택사항)
5. **추가 키워드**: 포함하거나 제외할 키워드가 있나요? (선택사항)

### 2단계: 검색 쿼리 생성 및 실행

수집한 정보를 바탕으로 검색을 실행합니다:

```bash
# 기본 검색
python search_papers.py --topic "연구주제" --count 30

# 연도 필터 포함
python search_papers.py --topic "연구주제" --count 30 --year-from 2020

# 추가 키워드 포함
python search_papers.py --topic "연구주제" --additional "키워드1,키워드2" --count 30

# 특정 키워드 제외
python search_papers.py --topic "연구주제" --exclude "제외키워드" --count 30
```

### 3단계: 결과 검토 및 선별

검색 결과를 다음 기준으로 분석하세요:

1. **관련성 평가**
   - 제목이 사용자의 검색 목적과 관련이 있는가?
   - 초록 내용이 사용자가 찾는 정보를 포함하는가?

2. **품질 평가**
   - 인용 횟수가 충분한가? (분야와 출판연도 고려)
   - 저명한 저널/학회에 게재되었는가?

3. **적합성 평가**
   - 사용자가 명시한 목적에 부합하는가?
   - 제외 조건에 해당하지 않는가?

### 4단계: 결과 보고

선별 결과를 다음 형식으로 보고하세요:

```markdown
## 논문 검색 결과 보고서

### 검색 조건
- **주제**: [연구 주제]
- **목적**: [검색 목적]
- **쿼리**: `[생성된 Scopus 쿼리]`
- **검색 결과**: 총 N편 중 M편 선별

### 추천 논문 (상위 순위)

#### 1. [논문 제목]
- **저자**: [저자명]
- **출판**: [저널명], [연도]
- **인용**: [인용수]회
- **DOI**: [DOI 링크]
- **선정 이유**: [이 논문이 사용자 목적에 적합한 이유]
- **초록 요약**: [2-3문장 요약]

[이하 반복...]

### 추가 검토 가능 논문
[관련성은 있으나 상위 추천에서 제외된 논문들]

### 검색 제안
[더 나은 결과를 위한 추가 검색 키워드나 필터 제안]
```

---

## 유용한 명령어

### 논문 검색
```bash
# 주제 기반 검색
python search_papers.py --topic "주제" --count 30

# 고급 쿼리 사용
python search_papers.py --query 'TITLE-ABS-KEY("term1") AND TITLE-ABS-KEY("term2")'

# 저장된 결과 로드
python search_papers.py --load data/papers/papers_YYYYMMDD_HHMMSS.json
```

### 저장된 결과 확인
```bash
ls -la data/papers/
```

---

## 주의사항

1. **API 키 확인**: 검색 전 `SCOPUS_API_KEY` 환경변수가 설정되어 있는지 확인
2. **API 제한**: Scopus API는 요청 제한이 있으므로 과도한 검색 자제
3. **결과 저장**: 검색 결과는 자동으로 `data/papers/` 디렉토리에 JSON으로 저장됨
4. **한글 주제**: 한글 주제도 검색 가능하나, 영문 키워드가 더 많은 결과를 반환함

---

## Scopus 검색 쿼리 문법

- `TITLE-ABS-KEY(term)`: 제목, 초록, 키워드에서 검색
- `TITLE(term)`: 제목에서만 검색
- `ABS(term)`: 초록에서만 검색
- `AUTH(name)`: 저자명 검색
- `PUBYEAR > 2020`: 연도 필터
- `AND`, `OR`, `AND NOT`: 불린 연산자
- 따옴표로 구문 검색: `"machine learning"`

예시:
```
TITLE-ABS-KEY("deep learning") AND TITLE-ABS-KEY("transformer") AND PUBYEAR > 2020
```
