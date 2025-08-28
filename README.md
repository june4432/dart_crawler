# DART 연결재무제표 주석 크롤러

한국 DART(Data Analysis, Retrieval and Transfer) 시스템에서 상장기업의 연결재무제표 주석을 자동으로 수집하고 저장하는 Python 크롤러입니다.

## 기능

- 회사명을 입력하면 DART 시스템에서 해당 회사의 고유번호를 자동으로 찾아줍니다
- 다양한 보고서 유형 지원 (사업보고서, 반기보고서, 분기보고서 등)
- 연결재무제표 주석을 HTML 및 텍스트 형태로 추출 및 저장
- 사용자 친화적인 콘솔 인터페이스

## 지원하는 보고서 유형

1. 사업보고서
2. 반기보고서
3. 분기보고서
4. 1분기보고서
5. 3분기보고서

## 설치

1. 저장소를 클론합니다:
```bash
git clone https://github.com/june4432/dart_crawler.git
cd dart_crawler
```

2. 필요한 패키지를 설치합니다:
```bash
pip install -r requirements.txt
```

3. 환경변수 설정을 위해 `.env` 파일을 생성합니다:
```
DART_API_KEY=your_dart_api_key_here
DART_CORP_CODE_URL=https://opendart.fss.or.kr/api/corpCode.xml
DART_LIST_URL=https://opendart.fss.or.kr/api/list.json
OUTPUT_DIR=result
```

## DART API 키 발급받기

1. [DART 전자공시시스템](https://opendart.fss.or.kr/) 접속
2. 상단 메뉴에서 "오픈API" 클릭
3. "개발가이드" → "신청·인증키 발급" → "인증키 신청"
4. 회원가입 후 인증키 발급신청
5. 발급받은 API 키를 `.env` 파일에 설정

## 사용법

```bash
python dart_crawler.py
```

프로그램 실행 후:
1. 조회할 회사명 입력 (예: "한솔피엔에스")
2. 보고서 유형 선택 (1-5)
3. 조회할 연도 입력 (예: "2025")
4. 결과 확인 후 파일 저장 여부 선택

## 출력 파일

조회된 연결재무제표 주석은 `result/` 디렉토리에 다음 형태로 저장됩니다:
- `{회사명}_{연도}_{보고서유형}_연결재무제표주석.html`
- `{회사명}_{연도}_{보고서유형}_연결재무제표주석.txt`

## 의존성

- `requests`: HTTP 요청 처리
- `python-dotenv`: 환경변수 관리
- `beautifulsoup4`: HTML 파싱
- `OpenDartReader`: DART API 인터페이스
- 기본 Python 라이브러리: `zipfile`, `xml.etree.ElementTree`, `json`, `os`, `pathlib`, `re`

## 주의사항

- DART API 키가 필요합니다 (무료)
- 네트워크 연결이 필요합니다
- 일부 회사나 연도의 경우 연결재무제표 주석이 존재하지 않을 수 있습니다
- API 호출 제한이 있을 수 있으니 과도한 요청은 피해주세요

## 라이선스

MIT License

## 기여

버그 리포트나 기능 제안은 GitHub Issues를 통해 해주세요.