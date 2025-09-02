from table_extractor import TableExtractor

# 최종 정리된 테스트
html_file = "result/한솔피엔에스_2025_반기보고서_연결재무제표주석.html"
extractor = TableExtractor(html_file)
success = extractor.extract_all_tables()

if success:
    print("✅ 최종 정리 테스트 성공!")
    
    # CSV 파일의 4번 항목 구분 컬럼 확인
    with open("result/한솔피엔에스_2025_반기보고서_표데이터.csv", 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        
    print("\n📊 4번 항목 (구분 컬럼 정리 확인):")
    for i, line in enumerate(lines):
        if ',4,' in line:
            print(f"행 {i+1}: {line.strip()}")
            # 헤더도 확인
            if i > 0 and '회사명' in lines[i-1]:
                print(f"헤더: {lines[i-1].strip()}")
                # 구분 컬럼 개수 확인
                header_parts = lines[i-1].strip().split(',')
                section_count = header_parts.count('구분')
                print(f"💡 구분 컬럼 개수: {section_count}")
                print()
                
else:
    print("❌ 테스트 실패!")
