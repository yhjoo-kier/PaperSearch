# PaperSearch

Scopus API를 활용한 학술 논문 검색 및 AI 에이전트 기반 선별 프레임워크

## 개요

이 프로젝트는 Claude Code 등의 CLI AI 에이전트가 학술 논문을 검색하고 사용자의 연구 목적에 맞는 논문을 선별하는 워크플로우를 제공합니다.

## 주요 기능

- ✅ Scopus API를 통한 학술 논문 검색
- ✅ AI 에이전트(Claude Code)를 활용한 키워드 확장 및 논문 선별
- ✅ 다양한 검색 옵션 (주제, 연도, 키워드 추가/제외)
- ✅ 검색 결과 JSON 저장 및 재사용
- ✅ 인용 수, 저널 품질, 관련성 기반 자동 선별

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 SCOPUS_API_KEY 설정
```

### Windows 환경 주의사항

Windows에서 특수문자 인코딩 오류가 발생하는 경우:

```bash
# PowerShell
$env:PYTHONIOENCODING="utf-8"
python search_papers.py --topic "..." --count 30

# CMD
set PYTHONIOENCODING=utf-8
python search_papers.py --topic "..." --count 30
```

또는 가상환경에서 실행:

```bash
.venv/Scripts/python.exe search_papers.py --topic "..." --count 30
```

## 사용법

### CLI 직접 사용

#### 기본 검색

```bash
# 주제로 검색 (기본 30편)
python search_papers.py --topic "machine learning" --count 30

# 연도 필터 추가
python search_papers.py --topic "transformer" --year-from 2020 --count 50
```

#### 고급 검색 옵션

```bash
# 추가 키워드 포함 (AND 조건)
# 주의: 모든 키워드를 만족하는 논문만 검색하므로 결과가 매우 제한적일 수 있음
python search_papers.py --topic "deep learning" --additional "attention,BERT" --count 30

# 키워드 제외
python search_papers.py --topic "deep learning" --exclude "survey,review" --count 30

# 커스텀 쿼리 직접 작성 (권장: 복잡한 검색)
python search_papers.py --query 'TITLE-ABS-KEY("topology optimization") AND TITLE-ABS-KEY("heat sink" OR "thermal management" OR "cooling")' --count 30
```

#### 실제 사용 예시

```bash
# 예시 1: 최근 5년간 히트 싱크 토폴로지 최적화 논문
python search_papers.py --query 'TITLE-ABS-KEY("topology optimization") AND TITLE-ABS-KEY("heat sink" OR "thermal management" OR "heat exchanger" OR "cooling") AND PUBYEAR > 2019' --count 30

# 예시 2: Transformer 기반 시계열 예측 (2020년 이후)
python search_papers.py --topic "transformer time series forecasting" --year-from 2020 --count 50

# 예시 3: 강화학습 관련 (리뷰 논문 제외)
python search_papers.py --topic "reinforcement learning" --exclude "review,survey" --year-from 2021 --count 40
```

#### 저장된 결과 재사용

```bash
# 저장된 결과 로드 (재검색 없이 분석만)
python search_papers.py --load data/papers/papers_20241201_120000.json

# 저장된 결과 확인
ls -la data/papers/
```

### Claude Code와 함께 사용 (권장)

Claude Code를 사용하면 AI가 자동으로 키워드를 확장하고 논문을 선별해줍니다.

1. 이 프로젝트 디렉토리에서 Claude Code 실행
2. `/paper-search` 슬래시 커맨드 사용 또는 자연어로 요청
   - 예: "Topology optimization of heat sink 관련 문헌 조사를 하자. 최근 5년 이내 연구 트렌드를 파악하고 싶어."
3. Claude Code가 자동으로:
   - 키워드 확장 (동의어, 하위 개념, 관련 용어)
   - 최적의 검색 쿼리 생성
   - 논문 검색 실행
   - 결과 분석 및 선별
   - 연구 트렌드 보고서 작성

#### Claude Code 사용의 장점

- **자동 키워드 확장**: AI가 관련 용어를 자동으로 찾아 검색 범위 최적화
- **스마트 쿼리 생성**: OR/AND 연산자를 적절히 조합하여 효율적인 검색
- **결과 분석**: 인용 수, 출판 저널, 관련성을 종합적으로 평가
- **트렌드 분석**: 연도별, 키워드별 연구 동향 파악

## 프로젝트 구조

```
PaperSearch/
├── CLAUDE.md              # Claude Code 워크플로우 정의
├── search_papers.py       # 메인 CLI 스크립트
├── src/
│   ├── scopus_client.py   # Scopus API 클라이언트
│   ├── query_builder.py   # 검색 쿼리 빌더
│   └── paper_fetcher.py   # 논문 가져오기 및 저장
├── data/
│   └── papers/            # 검색 결과 JSON 저장
└── .claude/
    └── commands/          # 슬래시 커맨드 정의
        └── paper-search.md
```

## 검색 팁

### 효과적인 검색 전략

1. **--topic vs --query**
   - `--topic`: 간단한 검색에 적합 (단일 구문)
   - `--query`: 복잡한 검색에 적합 (OR/AND 연산자 사용)

2. **--additional 옵션 주의사항**
   - 모든 키워드를 AND로 연결하므로 결과가 매우 제한적
   - 포괄적인 검색이 필요하면 `--query`로 OR 연산자 사용 권장

3. **Claude Code 활용 권장**
   - 수동으로 쿼리를 작성하는 대신 Claude Code에게 자연어로 요청
   - AI가 자동으로 최적의 검색 전략 수립

### 일반적인 문제 해결

#### 검색 결과가 너무 적을 때
```bash
# 나쁜 예: AND로 너무 많은 조건
python search_papers.py --topic "A" --additional "B,C,D,E"

# 좋은 예: OR로 관련 용어 포함
python search_papers.py --query 'TITLE-ABS-KEY("A") AND (TITLE-ABS-KEY("B") OR TITLE-ABS-KEY("C"))'
```

#### UnicodeEncodeError 발생 시
```bash
# 환경변수 설정
set PYTHONIOENCODING=utf-8  # Windows CMD
$env:PYTHONIOENCODING="utf-8"  # PowerShell
```

## Scopus 쿼리 문법 참고

- `TITLE-ABS-KEY(term)`: 제목, 초록, 키워드에서 검색
- `TITLE(term)`: 제목에서만 검색
- `AUTH(name)`: 저자명 검색
- `PUBYEAR > 2020`: 연도 필터
- `AND`, `OR`, `AND NOT`: 불린 연산자
- `"exact phrase"`: 정확한 구문 검색

예시:
```
TITLE-ABS-KEY("machine learning") AND (TITLE-ABS-KEY("NLP") OR TITLE-ABS-KEY("computer vision")) AND PUBYEAR > 2020
```

## API 키 발급

Scopus API 키는 [Elsevier Developer Portal](https://dev.elsevier.com/)에서 발급받을 수 있습니다.

1. 계정 생성 또는 로그인
2. "Create API Key" 선택
3. API 키를 `.env` 파일에 설정

## 제한사항

- Scopus API는 기관 IP 또는 개인 계정 기반 접근 제한 있음
- 무료 API 키는 일일 요청 수 제한 (보통 5,000 - 20,000 요청/주)
- 검색 결과는 Scopus 데이터베이스에 색인된 논문으로 제한

## 라이선스

MIT License
