import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import json
import os
from pathlib import Path
from typing import Union, Dict, List, Optional
from bs4 import BeautifulSoup
import re
from OpenDartReader.dart import OpenDartReader
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 환경변수에서 설정값 가져오기
api_key = os.getenv('DART_API_KEY')
corp_code_url_base = os.getenv('DART_CORP_CODE_URL', 'https://opendart.fss.or.kr/api/corpCode.xml')
list_url = os.getenv('DART_LIST_URL', 'https://opendart.fss.or.kr/api/list.json')
output_dir = Path(os.getenv('OUTPUT_DIR', 'result'))

# API 키 검증
if not api_key:
    raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")

# DART에서 제공하는 전체 회사 고유번호 목록 URL
corp_code_url = f"{corp_code_url_base}?crtfc_key={api_key}"

# 보고서 코드 매핑
REPORT_CODES = {
    "1": {"name": "사업보고서", "code": "11011"},
    "2": {"name": "반기보고서", "code": "11014"},
    "3": {"name": "분기보고서", "code": "11013"},
    "4": {"name": "1분기보고서", "code": "11012"},
    "5": {"name": "3분기보고서", "code": "11015"}
}

def get_corp_code(company_name: str) -> Optional[str]:
    """회사명을 입력받아 DART 고유번호를 반환합니다."""
    try:
        # URL 요청하여 zip 파일 다운로드
        res = requests.get(corp_code_url)
        res.raise_for_status()

        # 메모리 상에서 zip 파일 압축 해제
        zip_file = zipfile.ZipFile(io.BytesIO(res.content))
        xml_data = zip_file.read('CORPCODE.xml')

        # XML 파싱
        root = ET.fromstring(xml_data)
        
        for company in root.findall('.//list'):
            corp_name = company.find('corp_name').text
            corp_code = company.find('corp_code').text
            
            if corp_name == company_name:
                return corp_code
        return None
    except Exception as e:
        print(f"회사 고유번호 조회 중 오류: {e}")
        return None

def get_consolidated_financial_notes(company_name: str, year: str, report_type: str) -> Optional[Dict]:
    """
    특정 회사의 연결재무제표 주석을 가져옵니다.
    
    Args:
        company_name (str): 회사명
        year (str): 연도
        report_type (str): 보고서 유형 (1-5)
    
    Returns:
        dict: 주석 정보 (성공 시) 또는 None (실패 시)
    """
    try:
        print(f"=== {company_name} {year}년 {REPORT_CODES[report_type]['name']} 연결재무제표 주석 조회 ===")
        
        # 1단계: 회사 고유번호 찾기
        print(f"\n1️⃣ 회사 고유번호 조회 중...")
        corp_code = get_corp_code(company_name)
        if not corp_code:
            print(f"❌ '{company_name}'의 고유번호를 찾을 수 없습니다.")
            return None
        
        print(f"✅ 회사 고유번호: {corp_code}")
        
        # 2단계: 보고서 목록 조회
        print(f"\n2️⃣ {year}년도 보고서 목록 조회 중...")
        reports = get_report_list(corp_code, year, REPORT_CODES[report_type]['code'])
        if not reports:
            print(f"❌ {year}년도에 해당하는 보고서를 찾을 수 없습니다.")
            return None
        
        print(f"✅ {len(reports)}개의 보고서를 찾았습니다.")
        
        # 3단계: 각 보고서에서 연결재무제표 주석 찾기
        for i, report in enumerate(reports):
            rcept_no = report.get('rcept_no')
            rcept_dt = report.get('rcept_dt')
            
            print(f"\n3️⃣ {i+1}번째 보고서 처리 중...")
            print(f"   📋 접수번호: {rcept_no}")
            print(f"   📅 접수일자: {rcept_dt}")
            
            # 4단계: 하위 서류 목록 조회
            notes_info = get_consolidated_notes_from_report(rcept_no)
            if notes_info:
                print(f"✅ 연결재무제표 주석을 성공적으로 찾았습니다!")
                return {
                    'company_name': company_name,
                    'year': year,
                    'report_type': REPORT_CODES[report_type]['name'],
                    'rcept_no': rcept_no,
                    'rcept_dt': rcept_dt,
                    'notes_title': notes_info['title'],
                    'notes_url': notes_info['url'],
                    'html_content': notes_info['html_content'],
                    'text_content': notes_info['text_content'],
                    'html_length': len(notes_info['html_content']),
                    'text_length': len(notes_info['text_content'])
                }
            else:
                print(f"❌ 이 보고서에서 연결재무제표 주석을 찾을 수 없습니다.")
        
        print(f"\n❌ {year}년도 모든 보고서에서 연결재무제표 주석을 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        print(f"❌ 연결재무제표 주석 조회 중 오류: {e}")
        return None

def get_report_list(corp_code: str, year: str, report_code: str) -> Optional[List[Dict]]:
    """특정 회사의 보고서 목록을 조회합니다."""
    # 여러 연도로 시도 (DART API는 공시 연도와 다를 수 있음)
    years_to_try = [year, str(int(year)-1), str(int(year)-2)]
    
    for try_year in years_to_try:
        print(f"   🔍 {try_year}년도로 시도 중...")
        
        try:
            # 직접 DART API로 보고서 목록 조회
            
            params = {
                'crtfc_key': api_key,
                'corp_code': corp_code,
                'bgn_de': f"{try_year}0101",
                'end_de': f"{try_year}1231",
                'pblntf_ty': 'A',  # 정기공시
                'page_no': 1,
                'page_count': 100
            }
            
            res = requests.get(list_url, params=params)
            res.raise_for_status()
            
            data = res.json()
            
            if data.get('status') != '000':
                print(f"      ❌ API 오류: {data.get('message')}")
                continue
            
            print(f"      ✅ API 응답: {data.get('message')}")
            print(f"      📊 데이터 개수: {len(data.get('list', []))}")
            
            if len(data.get('list', [])) == 0:
                print(f"      ❌ 데이터가 없습니다.")
                continue
            
            # 해당 보고서 유형의 보고서만 필터링
            target_reports = []
            for item in data.get('list', []):
                report_name = item.get('report_nm', '')
                
                # 보고서 제목에 해당 유형이 포함되어 있는지 확인
                if report_code == "11014" and "반기보고서" in report_name:
                    target_reports.append(item)
                elif report_code == "11013" and "분기보고서" in report_name:
                    target_reports.append(item)
                elif report_code == "11011" and "사업보고서" in report_name:
                    target_reports.append(item)
                elif report_code == "11012" and "1분기보고서" in report_name:
                    target_reports.append(item)
                elif report_code == "11015" and "3분기보고서" in report_name:
                    target_reports.append(item)
            
            if target_reports:
                print(f"      🎯 {len(target_reports)}개의 해당 보고서를 찾았습니다!")
                return target_reports
            else:
                print(f"      ❌ 해당 보고서 유형을 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"      ❌ 처리 중 오류: {e}")
            continue
    
    return None

def get_notes_content_from_url(url: str) -> Optional[Dict]:
    """URL에서 주석 내용을 가져옵니다."""
    try:
        print(f"         📥 URL에서 내용 가져오는 중...")
        
        # 세션 생성하여 세션 유지
        session = requests.Session()
        
        # 먼저 메인 페이지에 접속하여 세션 생성
        main_url = url.split('?')[0] + '?' + '&'.join([p for p in url.split('?')[1].split('&') if not p.startswith('rcpNo=')])
        session.get(main_url)
        
        # 주석 페이지 접속
        response = session.get(url)
        response.raise_for_status()
        
        # HTML 원본과 정리된 텍스트 모두 반환
        html_content = response.content.decode('utf-8')
        
        # BeautifulSoup으로 파싱하여 텍스트도 추출
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # JavaScript 코드 제거
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 텍스트 추출
        text_content = soup.get_text()
        
        # 정리
        clean_text = re.sub(r'\s+', ' ', text_content).strip()
        
        if len(clean_text) > 100:  # 의미있는 내용이 있는 경우만
            print(f"         ✅ 내용 추출 성공! (HTML: {len(html_content)} 문자, 텍스트: {len(clean_text)} 문자)")
            return {
                'html': html_content,
                'text': clean_text
            }
        else:
            print(f"         ❌ 추출된 내용이 너무 짧습니다.")
            return None
            
    except Exception as e:
        print(f"         ❌ URL에서 내용 가져오기 실패: {e}")
        return None

def get_consolidated_notes_from_report(rcept_no: str) -> Optional[Dict]:
    """특정 보고서에서 연결재무제표 주석 정보를 가져옵니다."""
    try:
        # OpenDartReader 객체 생성
        dart = OpenDartReader(api_key)
        
        print(f"   4️⃣ OpenDartReader로 하위 서류 조회 중...")
        
        # 하위 서류 목록 가져오기
        sub_reports = dart.sub_docs(rcept_no)
        
        if sub_reports is None or len(sub_reports) == 0:
            print(f"      ❌ 하위 서류를 찾을 수 없습니다.")
            return None
        
        print(f"      ✅ 하위 서류 {len(sub_reports)}개를 찾았습니다!")
        
        # 연결재무제표 주석 관련 하위 서류 찾기
        for idx, sub_report in sub_reports.iterrows():
            title = sub_report.get('title', '')
            url = sub_report.get('url', '')
            
            print(f"         {idx+1:2d}. {title}")
            
            if '연결재무제표 주석' in title:
                print(f"         🎯 연결재무제표 주석을 찾았습니다!")
                
                # 해당 URL에서 내용 가져오기
                content_info = get_notes_content_from_url(url)
                if content_info:
                    return {
                        'title': title,
                        'url': url,
                        'html_content': content_info['html'],
                        'text_content': content_info['text']
                    }
                else:
                    print(f"         ❌ 내용 추출에 실패했습니다.")
                    continue
        
        print(f"      ❌ 연결재무제표 주석 관련 하위 서류를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        print(f"      ❌ 하위 서류 조회 중 오류: {e}")
        return None

def select_report_type() -> str:
    """사용자가 보고서 유형을 선택하도록 합니다."""
    print("\n=== 보고서 유형 선택 ===")
    for key, value in REPORT_CODES.items():
        print(f"{key}. {value['name']}")
    
    while True:
        choice = input("\n보고서 유형을 선택하세요 (1-5): ")
        if choice in REPORT_CODES:
            selected_report = REPORT_CODES[choice]
            print(f"✅ 선택된 보고서: {selected_report['name']}")
            return choice
        else:
            print("❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.")

def display_notes_result(result: Dict) -> None:
    """주석 조회 결과를 표시합니다."""
    print(f"\n{'='*80}")
    print(f"📊 연결재무제표 주석 조회 결과")
    print(f"{'='*80}")
    print(f"🏢 회사명: {result['company_name']}")
    print(f"📅 연도: {result['year']}")
    print(f"📋 보고서 유형: {result['report_type']}")
    print(f"🔢 접수번호: {result['rcept_no']}")
    print(f"📅 접수일자: {result['rcept_dt']}")
    print(f"📝 주석 제목: {result['notes_title']}")
    print(f"🔗 주석 URL: {result['notes_url']}")
    print(f"📏 HTML 길이: {result['html_length']:,} 문자")
    print(f"📏 텍스트 길이: {result['text_length']:,} 문자")
    print(f"{'='*80}")
    
    # 텍스트 내용 표시 (일부만)
    text_content = result['text_content']
    if len(text_content) > 3000:
        print(f"\n📖 주석 내용 (텍스트, 앞부분):")
        print(f"{'-'*80}")
        print(text_content[:3000] + "...")
        print(f"\n📖 주석 내용 (텍스트, 뒷부분):")
        print(f"{'-'*80}")
        print("..." + text_content[-1000:])
        print(f"\n📊 전체 텍스트 길이: {len(text_content):,} 문자")
    else:
        print(f"\n📖 주석 내용 (텍스트):")
        print(f"{'-'*80}")
        print(text_content)

def save_notes_to_files(result: Dict, company_name: str, year: str, report_type: str) -> bool:
    """주석 내용을 HTML과 텍스트 파일로 저장합니다."""
    try:
        # 출력 디렉토리 생성
        output_dir.mkdir(exist_ok=True)
        
        # HTML 파일 저장
        html_filename = output_dir / f"{company_name}_{year}_{REPORT_CODES[report_type]['name']}_연결재무제표주석.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} {year}년 {REPORT_CODES[report_type]['name']} 연결재무제표 주석</title>
    <style>
        body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ color: #2c3e50; margin: 0 0 10px 0; }}
        .header p {{ margin: 5px 0; color: #555; }}
        .content {{ background-color: white; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .highlight {{ background-color: #fff3cd; padding: 2px 4px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 {company_name} {year}년 {REPORT_CODES[report_type]['name']} 연결재무제표 주석</h1>
        <p><strong>🏢 회사명:</strong> {company_name}</p>
        <p><strong>📅 연도:</strong> {year}</p>
        <p><strong>📋 보고서 유형:</strong> {REPORT_CODES[report_type]['name']}</p>
        <p><strong>🔢 접수번호:</strong> {result['rcept_no']}</p>
        <p><strong>📅 접수일자:</strong> {result['rcept_dt']}</p>
        <p><strong>📝 주석 제목:</strong> {result['notes_title']}</p>
        <p><strong>🔗 주석 URL:</strong> <a href="{result['notes_url']}" target="_blank">{result['notes_url']}</a></p>
        <p><strong>📏 HTML 길이:</strong> {result['html_length']:,} 문자</p>
        <p><strong>📏 텍스트 길이:</strong> {result['text_length']:,} 문자</p>
    </div>
    
    <div class="content">
        <h2>📖 연결재무제표 주석 내용</h2>
        <hr>
        {result['html_content']}
    </div>
</body>
</html>""")
        
        print(f"✅ HTML 파일 저장 완료: {html_filename}")
        
        # 텍스트 파일도 저장
        text_filename = output_dir / f"{company_name}_{year}_{REPORT_CODES[report_type]['name']}_연결재무제표주석.txt"
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(f"회사명: {company_name}\n")
            f.write(f"연도: {year}\n")
            f.write(f"보고서 유형: {REPORT_CODES[report_type]['name']}\n")
            f.write(f"접수번호: {result['rcept_no']}\n")
            f.write(f"접수일자: {result['rcept_dt']}\n")
            f.write(f"주석 제목: {result['notes_title']}\n")
            f.write(f"주석 URL: {result['notes_url']}\n")
            f.write(f"{'='*80}\n\n")
            f.write(result['text_content'])
        
        print(f"✅ 텍스트 파일 저장 완료: {text_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 DART 연결재무제표 주석 크롤러")
    print("=" * 50)
    
    # 회사명 입력 받기
    company_name = input("🔍 조회할 회사명을 입력하세요: ")
    
    # 보고서 유형 선택
    report_type = select_report_type()
    
    # 연도 입력
    year = input(f"\n📅 {company_name}의 재무제표 주석을 조회할 연도를 입력하세요 (예: 2025): ")
    
    # 연결재무제표 주석 조회
    result = get_consolidated_financial_notes(company_name, year, report_type)
    
    if result:
        # 결과 표시
        display_notes_result(result)
        
        # 파일로 저장할지 묻기
        save_choice = input(f"\n💾 주석 내용을 파일로 저장하시겠습니까? (y/n): ").lower()
        if save_choice in ['y', 'yes', 'ㅇ']:
            save_notes_to_files(result, company_name, year, report_type)
    else:
        print(f"\n❌ 연결재무제표 주석을 가져올 수 없습니다.")

if __name__ == "__main__":
    main()
