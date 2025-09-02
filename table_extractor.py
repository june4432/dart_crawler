import csv
import re
import html
import json
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class TableExtractor:
    """HTML 파일에서 표 데이터를 추출하여 CSV로 변환하는 클래스"""
    
    def __init__(self, html_file_path: str):
        """
        Args:
            html_file_path (str): HTML 파일 경로
        """
        self.html_file_path = Path(html_file_path)
        self.soup = None
        self.company_info = {}
        
    def parse_html(self) -> bool:
        """HTML 파일을 파싱합니다."""
        try:
            with open(self.html_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.soup = BeautifulSoup(content, 'html.parser')
            return True
        except Exception as e:
            print(f"❌ HTML 파일 파싱 실패: {e}")
            return False
    
    def extract_basic_info(self) -> Dict[str, str]:
        """HTML에서 기본 정보(회사명, 연도, 보고서구분)를 추출합니다."""
        try:
            # 헤더 정보에서 추출
            header_div = self.soup.find('div', class_='header')
            if header_div:
                # 회사명 추출
                company_match = re.search(r'회사명:</strong>\s*([^<]+)', str(header_div))
                company = company_match.group(1).strip() if company_match else "알 수 없음"
                
                # 연도 추출  
                year_match = re.search(r'연도:</strong>\s*([^<]+)', str(header_div))
                year = year_match.group(1).strip() if year_match else "알 수 없음"
                
                # 보고서 유형 추출
                report_match = re.search(r'보고서 유형:</strong>\s*([^<]+)', str(header_div))
                report_type = report_match.group(1).strip() if report_match else "알 수 없음"
                
                self.company_info = {
                    'company': company,
                    'year': year,
                    'report_type': report_type
                }
                
                print(f"✅ 기본 정보 추출 완료: {company} | {year} | {report_type}")
                return self.company_info
                
        except Exception as e:
            print(f"❌ 기본 정보 추출 실패: {e}")
            
        # 기본값 설정
        self.company_info = {
            'company': "한솔피엔에스",
            'year': "2025", 
            'report_type': "반기보고서"
        }
        return self.company_info
    
    def find_sections(self) -> Dict[str, BeautifulSoup]:
        """1. 지배기업의 개요 섹션에서 (1)~(7) 하위 섹션들을 찾습니다."""
        sections = {}
        
        try:
            # 지배기업의 개요 또는 회사의 개요 섹션 찾기
            overview_section = None
            section_title = None
            
            for p in self.soup.find_all('p'):
                text = p.get_text().strip()
                if text == "1. 지배기업의 개요":
                    overview_section = p
                    section_title = "1. 지배기업의 개요"
                    break
                elif text == "1. 회사의 개요":
                    overview_section = p
                    section_title = "1. 회사의 개요"
                    break
            
            if not overview_section:
                print("❌ '1. 지배기업의 개요' 또는 '1. 회사의 개요' 섹션을 찾을 수 없습니다.")
                return sections
            
            print(f"✅ '{section_title}' 섹션을 찾았습니다.")
            
            # (1)~(7) 패턴 찾기
            current_element = overview_section
            current_section = None
            section_content = []
            
            while current_element:
                current_element = current_element.find_next_sibling()
                if not current_element:
                    break
                
                # 다음 주요 섹션 (2. 로 시작)이면 중단
                if current_element.name == 'p' and re.match(r'^\d+\.', current_element.get_text().strip()):
                    break
                
                # (숫자) 패턴 찾기
                if current_element.name == 'p':
                    text = current_element.get_text().strip()
                    section_match = re.match(r'^\(([1-7])\)', text)
                    if section_match:
                        # 이전 섹션 저장
                        if current_section and section_content:
                            sections[current_section] = section_content
                        
                        # 새 섹션 시작
                        current_section = f"({section_match.group(1)})"
                        section_content = [current_element]
                        print(f"   📋 섹션 발견: {current_section} - {text[:50]}...")
                        continue
                
                # 현재 섹션에 요소 추가
                if current_section:
                    section_content.append(current_element)
            
            # 마지막 섹션 저장
            if current_section and section_content:
                sections[current_section] = section_content
            
            print(f"✅ 총 {len(sections)}개 섹션을 찾았습니다: {list(sections.keys())}")
            return sections
            
        except Exception as e:
            print(f"❌ 섹션 찾기 실패: {e}")
            return {}
    
    def extract_table_title_and_data(self, section_name: str, section_elements: List) -> List[Dict]:
        """섹션 내 표들과 제목을 추출합니다."""
        tables_data = []
        
        try:
            current_period = ""
            # 섹션 제목 추출 (예: "(1) 종속기업의 현황" → "종속기업의 현황")
            section_title = ""
            
                            # 첫 번째 요소에서 섹션 제목 추출
            if section_elements and section_elements[0].name == 'p':
                first_text = section_elements[0].get_text().strip()
                # (n) 뒤의 텍스트 추출
                section_match = re.match(r'^\([1-7]\)\s*(.+)', first_text)
                if section_match:
                    # 전체 제목에서 의미있는 부분 추출
                    full_title = section_match.group(1)
                    
                    # 각 섹션별로 적절한 제목 추출
                    if '현황' in full_title:
                        section_title = "종속기업의 현황"
                    elif '재무상태' in full_title:
                        section_title = "연결대상 종속기업의 요약재무상태"
                    elif '경영성과' in full_title:
                        section_title = "연결대상 종속기업의 요약경영성과"
                    elif '현금흐름' in full_title:
                        section_title = "연결대상 종속기업의 요약현금흐름"
                    else:
                        # 6번, 7번 등의 경우 실제 제목을 그대로 사용
                        # "다음과 같습니다" 앞까지만 가져오기
                        #if '다음과 같습니다' in full_title:
                        #    section_title = full_title.split('다음과 같습니다')[0].strip()
                        # 첫 번째 문장만 가져오기 (줄바꿈이나 긴 설명 제거)
                        #el
                        # if '\n' in full_title:
                        #     section_title = full_title.split('\n')[0].strip()
                        # 첫 문장이 너무 길면 적당히 자르기
                        # elif len(full_title) > 50:
                        #     # 마침표나 쉼표 기준으로 자르기
                             if '.' in full_title[:50]:
                                 section_title = full_title.split('.')[0].strip()
                             elif ',' in full_title[:50]:
                                 section_title = full_title.split(',')[0].strip()
                             else:
                                 section_title = full_title.strip()
                        # else:
                            # section_title = full_title.strip()
            
            for element in section_elements:
                # 기간구분 찾기 (< > 패턴)
                if element.name == 'p':
                    text = element.get_text()
                    # HTML 엔터티 디코딩
                    decoded_text = html.unescape(text)
                    
                    # <제목> 패턴 찾기
                    period_match = re.search(r'<([^>]+)>', decoded_text)
                    if period_match:
                        current_period = period_match.group(1)
                        print(f"      🏷️  기간구분 발견: {current_period}")
                
                # 표 데이터 추출
                elif element.name == 'table':
                    table_data = self.extract_table_content(element)
                    if table_data:
                        # 기간구분이 없으면 "없음"
                        final_period = current_period if current_period else "없음"
                        
                        tables_data.append({
                            'section_title': section_title,
                            'period': final_period,
                            'headers': table_data['headers'],
                            'raw_headers': table_data.get('raw_headers', table_data['headers']),
                            'unit': table_data.get('unit', ''),
                            'rows': table_data['rows']
                        })
                        print(f"      📊 표 데이터 추출 완료: {len(table_data['rows'])}행 (항목: {section_title}, 기간: {final_period})")
                        
                        # 기간구분 리셋 (다음 표를 위해)
                        current_period = ""
        
        except Exception as e:
            print(f"❌ 표 제목 및 데이터 추출 실패: {e}")
        
        return tables_data
    
    def extract_table_content(self, table_element) -> Optional[Dict]:
        """HTML 표에서 헤더와 데이터를 추출합니다."""
        try:
            headers = []
            rows = []
            raw_headers = []  # 단위 추출을 위한 원본 헤더
            unit_info = ""  # 단위 정보
            
            # 헤더 추출 (배경색이 회색인 행들)
            header_rows = table_element.find_all('tr')
            data_started = False
            header_structure = []  # 헤더 구조 정보 저장
            
            for tr in header_rows:
                cells = tr.find_all(['td', 'th'])
                if not cells:
                    continue
                
                # 단위 정보가 있는 행인지 확인 (colspan이 크고 단위가 포함된 경우)
                if len(cells) == 1 and cells[0].get('colspan'):
                    cell_text = cells[0].get_text().strip()
                    unit_match = re.search(r'\(단위:([^)]+)\)', cell_text)
                    if unit_match:
                        unit_info = unit_match.group(1)
                        print(f"         🎯 단위 정보 발견: '{unit_info}'")
                        continue
                
                # 헤더인지 데이터인지 판별 (배경색 체크)
                is_header = False
                row_info = []  # 각 셀의 정보 저장
                
                for cell in cells:
                    # 원본 텍스트 
                    raw_cell_text = cell.get_text().strip()
                    raw_cell_text = html.unescape(raw_cell_text)
                    raw_cell_text = re.sub(r'\s+', ' ', raw_cell_text).strip()
                    
                    # 정리된 텍스트
                    cell_text = self.clean_text(raw_cell_text)
                    
                    # colspan, rowspan 정보
                    colspan = int(cell.get('colspan', 1))
                    rowspan = int(cell.get('rowspan', 1))
                    
                    # 배경색이 회색이면 헤더로 판단
                    style = cell.get('style', '')
                    if 'background-color:#D7D7D7' in style or cell.name == 'th':
                        is_header = True
                    
                    # 셀 정보 저장
                    row_info.append({
                        'text': cell_text,
                        'raw_text': raw_cell_text,
                        'colspan': colspan,
                        'rowspan': rowspan
                    })
                
                if is_header and not data_started:
                    header_structure.append(row_info)
                elif row_info and not is_header:
                    data_started = True
                    # 데이터 행 처리
                    row_data = [cell['text'] for cell in row_info]
                    if len(row_data) > 1:
                        rows.append(row_data)
            
            # 헤더 구조를 분석하여 최종 헤더 생성
            if header_structure:
                headers, raw_headers = self.build_final_headers(header_structure)
            
            if headers and rows:
                return {
                    'headers': headers,
                    'raw_headers': raw_headers,
                    'unit': unit_info,
                    'rows': rows
                }
            
        except Exception as e:
            print(f"❌ 표 내용 추출 실패: {e}")
        
        return None
    
    def build_final_headers(self, header_structure):
        """헤더 구조를 분석하여 최종 헤더를 생성합니다."""
        if not header_structure:
            return [], []
        
        # 첫 번째 행의 구조를 기반으로 최종 컬럼 수 계산
        first_row = header_structure[0]
        total_cols = sum(cell['colspan'] for cell in first_row)
        
        # 최종 헤더 배열 초기화
        final_headers = [''] * total_cols
        final_raw_headers = [''] * total_cols
        
        # 첫 번째 헤더 행 처리
        col_idx = 0
        for cell in first_row:
            text = cell['text']
            raw_text = cell['raw_text']
            colspan = cell['colspan']
            
            if colspan == 1:
                # rowspan인 경우 해당 위치에 직접 설정
                final_headers[col_idx] = text
                final_raw_headers[col_idx] = raw_text
            else:
                # colspan인 경우 기본 텍스트만 저장 (나중에 두 번째 행과 병합)
                for i in range(colspan):
                    if col_idx + i < total_cols:
                        final_headers[col_idx + i] = text  # 임시로 기본 텍스트 저장
                        final_raw_headers[col_idx + i] = raw_text
            
            col_idx += colspan
        
        # 두 번째 헤더 행이 있으면 병합 처리
        if len(header_structure) > 1:
            second_row = header_structure[1]
            
            # 두 번째 행의 셀들을 첫 번째 행의 colspan 영역과 매핑
            second_col_idx = 0
            for i, cell in enumerate(first_row):
                if cell['colspan'] > 1:
                    # colspan 영역에 두 번째 행 데이터 병합
                    for j in range(cell['colspan']):
                        if second_col_idx < len(second_row):
                            base_text = cell['text']
                            sub_text = second_row[second_col_idx]['text']
                            
                            # 최종 위치 계산
                            final_pos = sum(prev_cell['colspan'] for prev_cell in first_row[:i]) + j
                            
                            if final_pos < total_cols:
                                final_headers[final_pos] = f"{base_text}_{sub_text}"
                                final_raw_headers[final_pos] = f"{cell['raw_text']}_{second_row[second_col_idx]['raw_text']}"
                            
                            second_col_idx += 1
        
        return final_headers, final_raw_headers
    
    def clean_text(self, text: str) -> str:
        """텍스트를 정리합니다."""
        if not text:
            return ""
        
        # HTML 엔터티 디코딩
        text = html.unescape(text)
        
        # 불필요한 공백 제거
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # 괄호 안의 단위 정보 제거 (단위 컬럼이 별도로 있으므로)
        text = re.sub(r'\(단위:[^)]*\)_?', '', text)
        
        return text
    
    def extract_unit_from_headers(self, headers: List[str]) -> str:
        """헤더에서 단위 정보를 추출합니다."""
        if not headers:
            return ""
        
        # 헤더에서 (단위:xxx) 패턴 찾기
        for header in headers:
            unit_match = re.search(r'\(단위:([^)]+)\)', header)
            if unit_match:
                return unit_match.group(1)
        
        return ""
    
    def should_pivot_table(self, section_name: str, section_title: str) -> bool:
        """표를 피벗해야 하는지 판단합니다."""
        # 7번 항목이고 특정 키워드가 있으면 피벗
        if section_name.strip('()') == '7' and ('비지배지분과의 거래' in section_title or '자본에 미치는 영향' in section_title):
            return True
        return False
    
    def pivot_table_data(self, tables_data: List[Dict]) -> List[Dict]:
        """세로 형태의 표를 가로로 피벗합니다."""
        if not tables_data:
            return tables_data
        
        # 모든 표에서 데이터 수집
        all_rows = []
        for table in tables_data:
            all_rows.extend(table['rows'])
        
        if not all_rows:
            return tables_data
        
        # 첫 번째 표 정보 사용
        base_table = tables_data[0]
        
        # 피벗된 헤더 생성: [각 행의 첫 번째 컬럼 값들] (구분 컬럼 제거)
        pivot_headers = []
        pivot_values = []
        
        # 각 행에서 첫 번째 컬럼(구분)과 두 번째 컬럼(값) 추출
        for row in all_rows:
            if len(row) >= 2:
                category = row[0]  # 구분 (예: 취득한 비지배지분의 장부금액)
                value = row[1]     # 값 (예: 19,818)
                
                pivot_headers.append(category)
                pivot_values.append(value)
        
        # 피벗된 데이터 행 생성 (구분 컬럼 없이)
        pivot_row = pivot_values
        
        # 새로운 표 데이터 구조 생성
        pivoted_table = {
            'section_title': base_table['section_title'],
            'period': '당반기',  # 기간구분을 당반기로 설정
            'headers': pivot_headers,
            'raw_headers': pivot_headers,  # 같은 값 사용
            'unit': base_table['unit'],
            'rows': [pivot_row]
        }
        
        return [pivoted_table]

    def convert_to_csv_format(self, section_name: str, tables_data: List[Dict]) -> List[List[str]]:
        """표 데이터를 CSV 형식으로 변환합니다."""
        csv_rows = []
        
        try:
            # 피벗이 필요한지 확인
            if tables_data and self.should_pivot_table(section_name, tables_data[0]['section_title']):
                tables_data = self.pivot_table_data(tables_data)
            
            # 같은 항목의 표들을 그룹화
            grouped_tables = {}
            
            for table in tables_data:
                section_title = table['section_title']
                
                # 항목번호에서 괄호 제거: (1) → 1
                item_number = section_name.strip('()')
                
                # 그룹 키: 항목번호 + 항목제목
                group_key = f"{item_number}_{section_title}"
                
                if group_key not in grouped_tables:
                    grouped_tables[group_key] = []
                grouped_tables[group_key].append(table)
            
            # 각 그룹별로 처리
            for group_key, tables in grouped_tables.items():
                # 그룹 내 모든 표의 헤더가 동일한지 확인
                first_headers = None
                headers_identical = True
                
                for table in tables:
                    current_headers = table['headers']
                    if first_headers is None:
                        first_headers = current_headers
                    elif first_headers != current_headers:
                        headers_identical = False
                        break
                
                print(f"      🔍 그룹 {group_key}: 헤더 동일 여부 = {headers_identical}")
                
                header_written = False
                
                for table in tables:
                    section_title = table['section_title']
                    period = table['period']
                    headers = table['headers']
                    raw_headers = table.get('raw_headers', headers)
                    rows = table['rows']
                    
                    # 메타데이터를 별도 컬럼들로 분리
                    company = self.company_info['company']
                    year = self.company_info['year']
                    report_type = self.company_info['report_type']
                    
                    # 항목번호에서 괄호 제거: (1) → 1
                    item_number = section_name.strip('()')
                    
                    # 단위 정보 사용 (표에서 직접 추출된 것)
                    unit = table.get('unit', '')
                    
                    # 헤더 행 추가 조건:
                    # 1) 헤더가 모두 동일한 경우: 첫 번째 표에서만 헤더 출력
                    # 2) 헤더가 다른 경우: 각 표마다 헤더 출력
                    should_write_header = False
                    if headers_identical:
                        # 헤더가 동일한 경우: 첫 번째만
                        should_write_header = not header_written
                    else:
                        # 헤더가 다른 경우: 항상
                        should_write_header = True
                    
                    if should_write_header and headers:
                        header_row = ['회사명', '년도', '보고서구분', '항목번호', '항목제목', '기간구분', '단위'] + headers
                        csv_rows.append(header_row)
                        header_written = True
                    
                    # 데이터 행들 추가
                    for row in rows:
                        # 헤더 개수에 맞춰 행 데이터 조정
                        adjusted_row = row[:len(headers)] if headers else row
                        while len(adjusted_row) < len(headers):
                            adjusted_row.append("")
                        
                        data_row = [company, year, report_type, item_number, section_title, period, unit] + adjusted_row
                        csv_rows.append(data_row)
        
        except Exception as e:
            print(f"❌ CSV 형식 변환 실패: {e}")
        
        return csv_rows
    
    def save_to_csv(self, csv_data: List[List[str]], output_filename: str) -> bool:
        """CSV 파일로 저장합니다."""
        try:
            output_path = Path(output_filename)
            output_path.parent.mkdir(exist_ok=True)
            
            # UTF-8 BOM을 추가하여 Excel에서도 한글이 제대로 표시되도록 함
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(csv_data)
            
            print(f"✅ CSV 파일 저장 완료: {output_path}")
            print(f"   📊 총 {len(csv_data)}행 저장됨")
            return True
            
        except Exception as e:
            print(f"❌ CSV 파일 저장 실패: {e}")
            return False
    
    def extract_all_tables(self) -> bool:
        """모든 표를 추출하여 CSV로 저장합니다."""
        print("🚀 HTML 표 데이터 추출 시작")
        print("=" * 50)
        
        # 1. HTML 파싱
        if not self.parse_html():
            return False
        
        # 2. 기본 정보 추출
        self.extract_basic_info()
        
        # 3. 섹션 찾기
        sections = self.find_sections()
        if not sections:
            print("❌ 추출할 섹션을 찾을 수 없습니다.")
            return False
        
        # 4. 각 섹션별로 표 추출
        all_csv_data = []
        
        for section_name, section_elements in sections.items():
            print(f"\n📋 {section_name} 섹션 처리 중...")
            
            tables_data = self.extract_table_title_and_data(section_name, section_elements)
            if tables_data:
                csv_data = self.convert_to_csv_format(section_name, tables_data)
                all_csv_data.extend(csv_data)
                print(f"   ✅ {len(tables_data)}개 표에서 {len(csv_data)}행 추출")
            else:
                print(f"   ❌ {section_name}에서 표를 찾을 수 없습니다.")
        
        # 5. CSV 파일 저장
        if all_csv_data:
            company = self.company_info['company']
            year = self.company_info['year']
            report_type = self.company_info['report_type']
            
            output_filename = f"result/{company}_{year}_{report_type}_표데이터.csv"
            return self.save_to_csv(all_csv_data, output_filename)
        else:
            print("❌ 추출된 표 데이터가 없습니다.")
            return False

class BatchTableExtractor:
    """JSON 설정 파일을 읽어서 여러 기업의 표 데이터를 일괄 처리하는 클래스"""
    
    def __init__(self, config_file: str = "companies_config.json"):
        """
        Args:
            config_file (str): 기업 정보가 담긴 JSON 설정 파일 경로
        """
        self.config_file = Path(config_file)
        self.config = None
        
    def load_config(self) -> bool:
        """JSON 설정 파일을 로드합니다."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✅ 설정 파일 로드 완료: {len(self.config['companies'])}개 기업")
            return True
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
            return False
    
    def get_html_file_path(self, company_info: Dict[str, str]) -> str:
        """기업 정보를 바탕으로 HTML 파일 경로를 생성합니다."""
        company = company_info['company_name']
        year = company_info['year']
        report_type = company_info['report_type']
        
        # HTML 파일명 규칙: result/{회사명}_{년도}_{보고서종류}_연결재무제표주석.html
        html_filename = f"{company}_{year}_{report_type}_연결재무제표주석.html"
        return f"result/{html_filename}"
    
    def process_single_company(self, company_info: Dict[str, str]) -> bool:
        """단일 기업의 표 데이터를 처리합니다."""
        print(f"\n🏢 {company_info['company_name']} {company_info['year']} {company_info['report_type']} 처리 중...")
        
        html_file_path = self.get_html_file_path(company_info)
        
        # HTML 파일 존재 확인
        if not Path(html_file_path).exists():
            print(f"❌ HTML 파일을 찾을 수 없습니다: {html_file_path}")
            return False
        
        # 표 데이터 추출
        extractor = TableExtractor(html_file_path)
        success = extractor.extract_all_tables()
        
        if success:
            print(f"✅ {company_info['company_name']} 처리 완료")
        else:
            print(f"❌ {company_info['company_name']} 처리 실패")
            
        return success
    
    def process_all_companies(self) -> bool:
        """모든 기업의 표 데이터를 일괄 처리합니다."""
        if not self.config:
            print("❌ 설정이 로드되지 않았습니다. load_config()을 먼저 실행하세요.")
            return False
        
        success_count = 0
        total_count = len(self.config['companies'])
        
        print(f"\n🚀 {total_count}개 기업의 표 데이터 추출을 시작합니다...")
        
        for company_info in self.config['companies']:
            try:
                if self.process_single_company(company_info):
                    success_count += 1
            except Exception as e:
                print(f"❌ {company_info['company_name']} 처리 중 오류 발생: {e}")
        
        print(f"\n📊 처리 결과: {success_count}/{total_count}개 기업 성공")
        return success_count == total_count

def main():
    """메인 실행 함수"""
    # JSON 설정 파일이 있으면 일괄 처리, 없으면 기본 단일 처리
    config_file = "companies_config.json"
    
    if Path(config_file).exists():
        # 일괄 처리 모드
        batch_extractor = BatchTableExtractor(config_file)
        if batch_extractor.load_config():
            success = batch_extractor.process_all_companies()
            if success:
                print("\n🎉 모든 기업의 표 데이터 추출이 완료되었습니다!")
            else:
                print("\n⚠️ 일부 기업의 표 데이터 추출에 실패했습니다.")
        else:
            print("\n❌ 설정 파일 로드에 실패했습니다.")
    else:
        # 기본 단일 처리 모드 (기존 동작)
        html_file = "result/한솔피엔에스_2025_반기보고서_연결재무제표주석.html"
        
        extractor = TableExtractor(html_file)
        success = extractor.extract_all_tables()
        
        if success:
            print("\n🎉 표 데이터 추출이 완료되었습니다!")
        else:
            print("\n❌ 표 데이터 추출에 실패했습니다.")

if __name__ == "__main__":
    main()
