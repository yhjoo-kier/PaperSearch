# PaperSearch

Scopus API를 활용한 학술 논문 검색 및 AI 에이전트 기반 선별 프레임워크

## 개요

이 프로젝트는 Claude Code 등의 CLI AI 에이전트가 학술 논문을 검색하고 사용자의 연구 목적에 맞는 논문을 선별하는 워크플로우를 제공합니다.

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 SCOPUS_API_KEY 설정
```

## 사용법

### CLI 직접 사용

```bash
# 주제로 검색
python search_papers.py --topic "machine learning" --count 30

# 연도 필터 추가
python search_papers.py --topic "transformer" --year-from 2020 --count 50

# 키워드 추가/제외
python search_papers.py --topic "deep learning" --additional "attention,BERT" --exclude "survey"

# 저장된 결과 로드
python search_papers.py --load data/papers/papers_20241201_120000.json
```

### Claude Code와 함께 사용

1. 이 프로젝트 디렉토리에서 Claude Code 실행
2. `/paper-search` 슬래시 커맨드 사용
3. Claude Code의 안내에 따라 검색 조건 입력
4. AI가 검색 결과를 분석하고 적합한 논문 선별

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

## API 키 발급

Scopus API 키는 [Elsevier Developer Portal](https://dev.elsevier.com/)에서 발급받을 수 있습니다.

## 라이선스

MIT License
