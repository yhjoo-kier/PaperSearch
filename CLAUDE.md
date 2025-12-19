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
├── download_papers.py     # PDF 다운로드 CLI 스크립트
├── src/
│   ├── scopus_client.py   # Scopus API 클라이언트
│   ├── query_builder.py   # 검색 쿼리 빌더
│   ├── paper_fetcher.py   # 논문 가져오기 및 저장
│   └── pdf_downloader.py  # PDF 다운로더 (Unpaywall API 사용)
├── data/
│   ├── papers/            # 검색 결과 저장 디렉토리
│   └── pdfs/              # 다운로드된 PDF 저장 디렉토리
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

### 2단계: 키워드 확장

**검색 실행 전, 반드시 키워드를 확장하세요.**

사용자가 제공한 주제에 대해 당신의 지식을 활용하여 다음을 도출하세요:

1. **영문 변환**: 한글 주제를 영문 학술 용어로 변환
2. **동의어/유사어**: 같은 개념을 다르게 표현하는 용어들
3. **하위 개념**: 주제에 포함되는 세부 기술/방법론
4. **관련 키워드**: 해당 분야에서 함께 자주 언급되는 용어

**예시:**
```
사용자 입력: "transformer 기반 시계열 예측"

키워드 확장:
- 영문 변환: "transformer time series forecasting"
- 동의어: "temporal prediction", "sequence forecasting"
- 하위 개념: "Informer", "Autoformer", "PatchTST", "Temporal Fusion Transformer"
- 관련 키워드: "attention mechanism", "long-range dependency", "multivariate forecasting"
```

확장한 키워드 목록을 사용자에게 보여주고, 추가/제외할 키워드가 있는지 확인받으세요.

### 3단계: 검색 쿼리 생성 및 실행

확장된 키워드를 바탕으로 검색을 실행합니다:

#### 중요: 효과적인 쿼리 작성 전략

**`--additional` 옵션의 한계:**
- 모든 키워드를 AND 연산자로 연결하여 결과가 매우 제한적
- 확장 키워드를 모두 포함하는 논문만 검색 → 결과 0-1편

**권장: `--query` 옵션 사용**
- OR 연산자로 관련 용어를 유연하게 조합
- 주요 개념은 AND, 동의어/관련 용어는 OR로 연결

```bash
# ❌ 비권장: --additional (모든 키워드 AND)
python search_papers.py --topic "topology optimization heat sink" \
  --additional "thermal management,SIMP,electronics cooling,microchannel" \
  --count 30
# → 결과: 1편 (모든 조건을 만족하는 논문만 검색)

# ✅ 권장: --query (OR로 유연하게 조합)
python search_papers.py --query 'TITLE-ABS-KEY("topology optimization") AND TITLE-ABS-KEY("heat sink" OR "thermal management" OR "heat exchanger" OR "cooling") AND PUBYEAR > 2019' --count 30
# → 결과: 30편 (관련성 높은 논문 다수)
```

#### 검색 명령어 예시

```bash
# 1. 간단한 주제 검색 (단일 키워드)
python search_papers.py --topic "주요키워드" --count 30 --year-from 2020

# 2. 복잡한 검색 (추천)
python search_papers.py --query 'TITLE-ABS-KEY("핵심개념") AND (TITLE-ABS-KEY("관련개념1") OR TITLE-ABS-KEY("관련개념2") OR TITLE-ABS-KEY("관련개념3")) AND PUBYEAR > 2019' --count 30

# 3. 키워드 제외
python search_papers.py --topic "주요키워드" --exclude "제외키워드1,제외키워드2" --count 30
```

#### 실제 사용 예시

```bash
# 예시 1: 히트 싱크 토폴로지 최적화 (전자기기 냉각)
.venv/Scripts/python.exe search_papers.py --query 'TITLE-ABS-KEY("topology optimization") AND TITLE-ABS-KEY("heat sink" OR "thermal management" OR "heat exchanger" OR "cooling") AND PUBYEAR > 2019' --count 30

# 예시 2: Transformer 기반 시계열 예측
.venv/Scripts/python.exe search_papers.py --query 'TITLE-ABS-KEY("transformer") AND TITLE-ABS-KEY("time series" OR "temporal" OR "forecasting" OR "prediction") AND PUBYEAR > 2020' --count 50

# 예시 3: 강화학습 (리뷰 제외)
.venv/Scripts/python.exe search_papers.py --topic "reinforcement learning" --exclude "review,survey" --year-from 2021 --count 40
```

**팁**:
- 가상환경 Python 사용: `.venv/Scripts/python.exe` (Windows)
- 복잡한 쿼리는 반드시 `--query` 옵션 사용
- 인용부호 안에서는 공백 사용 가능

### 4단계: 결과 검토 및 선별

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

### 5단계: 결과 보고

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

### 6단계: PDF 다운로드 (선택사항)

사용자가 선별된 논문의 PDF 다운로드를 원하는 경우, 다음 절차를 따르세요:

1. **다운로드 가능 여부 확인**
   - DOI가 있는 논문만 다운로드 가능
   - Unpaywall API를 통해 오픈 액세스 PDF 검색

2. **다운로드 실행**
   ```bash
   # 대화형 모드 (추천) - 다운로드할 논문 선택
   python download_papers.py --latest

   # 특정 논문 번호 지정
   python download_papers.py --latest --select 1,3,5-10

   # DOI가 있는 모든 논문 다운로드
   python download_papers.py --latest --all
   ```

3. **결과 안내**
   - 다운로드 성공/실패 여부 보고
   - 오픈 액세스가 아닌 논문은 다운로드 불가
   - 다운로드된 파일 위치: `data/pdfs/`

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

### PDF 다운로드
```bash
# 대화형 모드 - 논문 목록에서 선택
python download_papers.py --latest

# 특정 파일에서 로드
python download_papers.py --load data/papers/papers_YYYYMMDD_HHMMSS.json

# 특정 논문만 다운로드 (번호로 지정)
python download_papers.py --latest --select 1,3,5-10

# DOI가 있는 모든 논문 다운로드
python download_papers.py --latest --all

# 다운로드 디렉토리 지정
python download_papers.py --latest --all --output-dir ./my_papers

# 논문 목록만 확인 (다운로드 안 함)
python download_papers.py --latest --list-only
```

### 다운로드된 PDF 확인
```bash
ls -la data/pdfs/
```

---

## 주의사항 및 문제 해결

### 일반 주의사항

1. **API 키 확인**: 검색 전 `SCOPUS_API_KEY` 환경변수가 설정되어 있는지 확인
2. **API 제한**: Scopus API는 요청 제한이 있으므로 과도한 검색 자제
3. **결과 저장**: 검색 결과는 자동으로 `data/papers/` 디렉토리에 JSON으로 저장됨
4. **한글 주제**: 한글 주제도 검색 가능하나, 영문 키워드가 더 많은 결과를 반환함
5. **PDF 다운로드**: Unpaywall API를 통해 오픈 액세스 논문만 다운로드 가능

### 문제 해결

#### 1. UnicodeEncodeError 발생 시

**증상**: `UnicodeEncodeError: 'cp949' codec can't encode character`

**원인**: Windows 터미널에서 특수문자(±, −, × 등) 출력 시 인코딩 오류

**해결 방법**:
```bash
# Windows CMD
set PYTHONIOENCODING=utf-8
.venv/Scripts/python.exe search_papers.py --query "..." --count 30

# PowerShell
$env:PYTHONIOENCODING="utf-8"
.venv/Scripts/python.exe search_papers.py --query "..." --count 30
```

또는 가상환경 Python을 직접 사용:
```bash
.venv/Scripts/python.exe search_papers.py --query "..." --count 30
```

#### 2. 검색 결과가 0-1편일 때

**원인**: `--additional` 옵션이 모든 키워드를 AND로 연결

**해결 방법**: `--query` 옵션으로 OR 연산자 사용
```bash
# 잘못된 방법
python search_papers.py --topic "A" --additional "B,C,D,E"

# 올바른 방법
python search_papers.py --query 'TITLE-ABS-KEY("A") AND (TITLE-ABS-KEY("B") OR TITLE-ABS-KEY("C"))'
```

#### 3. 검색 결과 파일 찾기

검색 결과는 타임스탬프와 함께 저장됩니다:
```bash
ls -la data/papers/
# papers_20251219_130800.json 형식
```

최신 파일을 찾으려면:
```bash
ls -lt data/papers/ | head -5
```

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
