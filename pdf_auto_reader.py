import sys
import time
import os
import shutil
import fitz  # PyMuPDF
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# PDF 파일이 들어올 폴더와 처리 후 이동될 폴더 경로 설정
WATCH_PATH = "./inbox"      # 감시할 폴더
PROCESSED_PATH = "./processed" # 처리 완료 후 이동할 폴더

# 폴더가 없는 경우 생성
os.makedirs(WATCH_PATH, exist_ok=True)
os.makedirs(PROCESSED_PATH, exist_ok=True)


def process_pdf(pdf_path):
    """
    주어진 경로의 PDF 파일에서 텍스트를 추출하는 함수
    """
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 처리 시작: {pdf_path}")

        # PDF 파일 열기
        doc = fitz.open(pdf_path)
        
        full_text = ""
        # 각 페이지를 순회하며 텍스트 추출
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += page.get_text()
            
        print("-" * 20)
        print("추출된 텍스트:")
        print(full_text.strip())
        print("-" * 20)
        
        # 문서 닫기
        doc.close()
        
        # 처리 완료된 파일을 processed 폴더로 이동
        file_name = os.path.basename(pdf_path)
        shutil.move(pdf_path, os.path.join(PROCESSED_PATH, file_name))
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 처리 완료 및 이동: {os.path.join(PROCESSED_PATH, file_name)}")

    except Exception as e:
        print(f"오류 발생: {pdf_path} 처리 중 오류가 발생했습니다. - {e}")
        # 오류 발생 시에도 파일을 이동시키려면 여기에 로직 추가 가능

import fitz  # PyMuPDF
import os
import json
import pandas as pd

# def extract_pdf_elements_with_context(pdf_path, output_folder='./json'):
#     """
#     PDF에서 텍스트, 표, 이미지를 추출하여 맥락을 유지하는 JSON 파일로 저장합니다.

#     Args:
#         pdf_path (str): 입력 PDF 파일 경로
#         output_folder (str): 결과물을 저장할 폴더 경로
#     """
#     # 결과물 저장 폴더 생성
#     if not os.path.exists(output_folder):
#         os.makedirs(output_folder)

#     try:
#         doc = fitz.open(pdf_path)
#     except Exception as e:
#         print(f"Error opening or processing PDF file: {e}")
#         return None

#     all_pages_data = []

#     # 각 페이지 순회
#     for page_num, page in enumerate(doc):
#         print(f"--- Processing Page {page_num + 1}/{len(doc)} ---")
#         page_elements = []
        
#         # 1. 이미지 추출
#         image_list = page.get_images(full=True)
#         img_dir = os.path.join(output_folder, f"page_{page_num + 1}_images")
#         if image_list and not os.path.exists(img_dir):
#             os.makedirs(img_dir)

#         for img_index, img in enumerate(image_list):
#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]
#             image_ext = base_image["ext"]
#             image_filename = f"image_{page_num + 1}_{img_index}.{image_ext}"
#             image_path = os.path.join(img_dir, image_filename)
            
#             with open(image_path, "wb") as img_file:
#                 img_file.write(image_bytes)
            
#             # 이미지의 위치 정보(bounding box) 가져오기
#             try:
#                 img_bbox = page.get_image_bbox(img)
#                 page_elements.append({
#                     "type": "image",
#                     "path": image_path,
#                     "bbox": [img_bbox.x0, img_bbox.y0, img_bbox.x1, img_bbox.y1]
#                 })
#             except ValueError:
#                 print(f"Warning: Could not determine bbox for image {img_index} on page {page_num + 1}")


#         # 2. 표 추출
#         # find_tables()는 페이지의 표를 자동으로 찾아줍니다.
#         tables = page.find_tables()
#         for i, table in enumerate(tables):
#             # 표의 위치 정보(bounding box)
#             table_bbox = table.bbox
            
#             # 표 내용 추출
#             table_data = table.extract()
#             # pandas DataFrame으로 변환하여 JSON으로 직렬화하기 쉽게 만듦
#             df = pd.DataFrame(table_data[1:], columns=table_data[0])

#             page_elements.append({
#                 "type": "table",
#                 "data": df.to_dict('records'), # 각 행을 dict의 list로 변환
#                 "bbox": list(table_bbox)
#             })

#         # 3. 텍스트 블록 추출
#         # "blocks" 옵션은 단락 단위로 텍스트와 위치 정보를 함께 제공합니다.
#         text_blocks = page.get_text("blocks")
#         for block in text_blocks:
#             # block[4]는 텍스트 내용, block[0:4]는 bbox 좌표입니다.
#             text_content = block[4].strip()
#             if text_content: # 빈 텍스트 블록은 제외
#                 page_elements.append({
#                     "type": "text",
#                     "content": text_content.replace('\n', ' '), # 줄바꿈을 공백으로 변환
#                     "bbox": list(block[0:4])
#                 })
        
#         # 4. 페이지 내 모든 요소들을 수직 위치(y0) 기준으로 정렬
#         # bbox는 (x0, y0, x1, y1) 형식이므로, y0는 bbox[1]입니다.
#         sorted_elements = sorted(page_elements, key=lambda el: el['bbox'][1])
        
#         all_pages_data.append({
#             "page_number": page_num + 1,
#             "elements": sorted_elements
#         })

#     # 5. 최종 결과를 JSON 파일로 저장
#     json_output_path = os.path.join(output_folder, "structured_output.json")
#     with open(json_output_path, 'w', encoding='utf-8') as f:
#         json.dump(all_pages_data, f, ensure_ascii=False, indent=4)
    
#     doc.close()
#     print(f"\nExtraction complete. Structured data saved to: {json_output_path}")
#     return json_output_path

# import fitz  # PyMuPDF
# import os
# import json
# import pandas as pd

# def extract_pdf_data_without_bbox(pdf_path, output_folder='./json'):
#     """
#     PDF에서 bbox 정보 없이 텍스트, 표, 이미지를 순서대로 추출합니다.
#     (주의: 문서의 시각적 순서와 다를 수 있습니다.)

#     Args:
#         pdf_path (str): 입력 PDF 파일 경로
#         output_folder (str): 결과물을 저장할 폴더 경로
#     """
#     # 결과물 저장 폴더 생성
#     if not os.path.exists(output_folder):
#         os.makedirs(output_folder)

#     try:
#         doc = fitz.open(pdf_path)
#     except Exception as e:
#         print(f"Error opening or processing PDF file: {e}")
#         return None

#     extracted_data = []

#     # 각 페이지 순회
#     for page_num, page in enumerate(doc):
#         print(f"--- Processing Page {page_num + 1}/{len(doc)} ---")
        
#         # 1. 텍스트 추출 (페이지 전체 텍스트를 하나의 문자열로)
#         # get_text()는 페이지의 텍스트를 읽는 순서에 가깝게 추출해 줍니다.
#         full_text = page.get_text("text")
#         if full_text.strip():
#             extracted_data.append({
#                 "page_number": page_num + 1,
#                 "type": "text",
#                 "content": full_text.strip()
#             })

#         # 2. 표 추출
#         tables = page.find_tables()
#         for i, table in enumerate(tables):
#             table_data = table.extract()
#             if not table_data or len(table_data) < 2: continue

#             df = pd.DataFrame(table_data[1:], columns=table_data[0])
#             extracted_data.append({
#                 "page_number": page_num + 1,
#                 "type": "table",
#                 "table_index_on_page": i + 1,
#                 "data": df.to_dict('records')
#             })

#         # 3. 이미지 추출
#         image_list = page.get_images(full=True)
#         if image_list:
#             img_dir = os.path.join(output_folder, f"page_{page_num + 1}_images")
#             if not os.path.exists(img_dir):
#                 os.makedirs(img_dir)

#             for img_index, img in enumerate(image_list):
#                 xref = img[0]
#                 try:
#                     base_image = doc.extract_image(xref)
#                     image_bytes = base_image["image"]
#                     image_ext = base_image["ext"]
#                     image_filename = f"image_{page_num + 1}_{img_index}.{image_ext}"
#                     image_path = os.path.join(img_dir, image_filename)
                    
#                     with open(image_path, "wb") as img_file:
#                         img_file.write(image_bytes)
                    
#                     extracted_data.append({
#                         "page_number": page_num + 1,
#                         "type": "image",
#                         "path": image_path
#                     })
#                 except Exception as e:
#                     print(f"Warning: Could not extract image {img_index} on page {page_num + 1}: {e}")
    
#     # 4. 최종 결과를 JSON 파일로 저장
#     json_output_path = os.path.join(output_folder, "simple_output.json")
#     with open(json_output_path, 'w', encoding='utf-8') as f:
#         json.dump(extracted_data, f, ensure_ascii=False, indent=4)
    
#     doc.close()
#     print(f"\nSimple extraction complete. Data saved to: {json_output_path}")
#     return json_output_path

import camelot
import json
import pandas as pd

import os
import json
import camelot
import pdfplumber
import pandas as pd

def extract_text_and_tables_from_pdf(pdf_path, output_folder='./json_output'):
    """
    PDF 문서의 모든 페이지에서 텍스트와 표를 추출하여 하나의 JSON 파일로 저장합니다.

    Args:
        pdf_path (str): 분석할 PDF 파일의 경로
        output_folder (str): 결과물을 저장할 폴더 경로
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    all_pages_data = []

    try:
        # pdfplumber로 PDF 열기
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages found: {len(pdf.pages)}")

            # 모든 페이지를 순회
            for i, page in enumerate(pdf.pages):
                page_number = i + 1
                print(f"Processing page {page_number}...")

                # 1. 페이지의 전체 텍스트 추출
                page_text = page.extract_text()

                # 2. Camelot을 사용하여 페이지의 표 추출 ('lattice' 방식 사용)
                try:
                    tables = camelot.read_pdf(pdf_path, pages=str(page_number), flavor='lattice')
                except Exception as e:
                    print(f"  - Camelot error on page {page_number}: {e}")
                    tables = [] # 오류 발생 시 빈 리스트로 처리

                page_tables_data = []
                if tables and tables.n > 0:
                    print(f"  - Found {tables.n} table(s) on page {page_number}.")
                    for table_index, table in enumerate(tables):
                        # --- 원본 코드의 데이터 클리닝 및 헤더 재설정 로직 유지 ---
                        df = table.df
                        
                        if df.empty or len(df.index) < 2:
                            print(f"  - Table {table_index + 1} on page {page_number} is empty or has no data rows. Skipping.")
                            continue

                        new_header = df.iloc[0]
                        df = df[1:]
                        df.columns = new_header
                        
                        # 첫 번째 열 이름이 비어있을 경우를 대비하여 확인 후 이름 변경
                        if df.columns[0] is not None and str(df.columns[0]).strip() != '':
                             df = df.rename(columns={df.columns[0]: 'row'})
                        else:
                            # 첫 번째 열 이름이 비어있다면 임의의 이름으로 지정하거나,
                            # 데이터의 첫 번째 셀을 이름으로 사용하는 등의 처리가 필요할 수 있습니다.
                            # 여기서는 'row'로 강제 지정합니다.
                            df.columns.values[0] = 'row'

                        df = df.applymap(lambda x: x.replace('\n', ' ') if isinstance(x, str) else x)

                        # 데이터를 JSON 형식(레코드 리스트)으로 변환
                        table_json = json.loads(df.to_json(orient='records', force_ascii=False))
                        
                        page_tables_data.append({
                            "table_index_on_page": table_index + 1,
                            "data": table_json
                        })
                else:
                    print(f"  - No tables found on page {page_number}.")
                
                # 현재 페이지의 모든 정보를 딕셔너리로 저장
                all_pages_data.append({
                    "page_number": page_number,
                    "text_content": page_text if page_text else "",
                    "tables": page_tables_data
                })

    except Exception as e:
        print(f"An error occurred while processing the PDF file: {e}")
        return

    # 전체 추출 데이터를 하나의 JSON 파일로 저장
    # 파일 이름은 원본 PDF 파일 이름을 기반으로 생성
    base_name = os.path.basename(pdf_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    json_output_path = os.path.join(output_folder, f"{file_name_without_ext}_full_extraction.json")

    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(all_pages_data, f, ensure_ascii=False, indent=4)

    print("\n--------------------------------------------------")
    print(f"Extraction complete for all pages.")
    print(f"Data saved to: {json_output_path}")
    print("--------------------------------------------------")

# # --- 스크립트 실행 ---
# if __name__ == '__main__':
#     # 예시 파라미터
#     pdf_file_path = "example.pdf"  # 실제 PDF 파일 경로
#     target_page = 3                # 사용자가 제공한 정보 기반
#     output_dir = "camelot_output"

#     if os.path.exists(pdf_file_path):
#         extract_table_with_camelot(pdf_file_path, target_page, output_dir)
#     else:
#         print(f"Error: The file '{pdf_file_path}' was not found.")

class PDFHandler(FileSystemEventHandler):
    """
    파일 시스템 이벤트를 처리하는 핸들러 클래스
    """
    def on_created(self, event):
        # 파일이 생성되었을 때 호출되는 메서드
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            # 파일이 생성되고 안정화될 시간을 잠시 줌 (파일 복사 중 접근 방지)
            time.sleep(1) 
            # process_pdf(event.src_path)
            extract_text_and_tables_from_pdf(event.src_path)


if __name__ == "__main__":
    # 이벤트 핸들러 및 옵저버 설정
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=False) # recursive=False는 하위 폴더는 감시 안 함

    print(f"'{WATCH_PATH}' 폴더에서 PDF 파일 모니터링을 시작합니다...")
    
    # 옵저버 시작
    observer.start()
    
    try:
        # 프로그램이 종료되지 않도록 무한 루프
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Ctrl+C로 종료 시 옵저버 중지
        observer.stop()
        print("모니터링을 중지합니다.")
        
    observer.join()