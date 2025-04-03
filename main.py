import fitz  # PyMuPDF
import cv2
from pyzbar.pyzbar import decode
from collections import OrderedDict
import os
import json

class PDFProcessor:
    def __init__(self, reference_dir='references'):
        self.reference_dir = reference_dir
        self.extracted_data = OrderedDict()
        self.expected_structure = self.load_reference()
        os.makedirs(self.reference_dir, exist_ok=True)
    
    def load_reference(self):
        if not os.path.exists(self.reference_dir):
            os.makedirs(self.reference_dir)

        reference_files = [f for f in os.listdir(self.reference_dir) if f.endswith('.json')]
        if reference_files:
            latest_reference = sorted(reference_files)[-1]
            with open(os.path.join(self.reference_dir, latest_reference), 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def extract_data(self, file_path):
        doc = fitz.open(file_path)
        full_text = []
        barcode_data = []
        barcode_positions = []

        for page_num, page in enumerate(doc):
            full_text += page.get_text("text").strip().split("\n")
            pix = page.get_pixmap()
            img_path = f"temp_page_{page_num}.png"
            pix.save(img_path)
            img = cv2.imread(img_path)
            barcodes = decode(img)
            os.remove(img_path)

            for barcode in barcodes:
                barcode_data.append(barcode.data.decode("utf-8"))
                barcode_positions.append((barcode.rect.left, barcode.rect.top))
        
        doc.close()
        self.extracted_data['TEXT'] = full_text
        self.extracted_data['BARCODES'] = barcode_data
        self.extracted_data['BARCODE_POSITIONS'] = [list(pos) for pos in barcode_positions]
        return self.extracted_data

    def compare_positions(self, expected, extracted, tolerance=5):
        if len(expected) != len(extracted):
            return False
        for (ex_x, ex_y), (ext_x, ext_y) in zip(expected, extracted):
            if abs(ex_x - ext_x) > tolerance or abs(ex_y - ext_y) > tolerance:
                return False
        return True

    def validate(self):
        if not self.expected_structure:
            return "Эталон отсутствует! Создайте его сначала."

        expected_text = self.expected_structure.get('TEXT', [])
        expected_barcodes = self.expected_structure.get('BARCODES', [])
        expected_positions = [tuple(pos) for pos in self.expected_structure.get('BARCODE_POSITIONS', [])]
        extracted_text = self.extracted_data.get('TEXT', [])
        extracted_barcodes = self.extracted_data.get('BARCODES', [])
        extracted_positions = self.extracted_data.get('BARCODE_POSITIONS', [])

        text_match = expected_text == extracted_text
        barcode_match = expected_barcodes == extracted_barcodes
        position_match = self.compare_positions(expected_positions, extracted_positions)
        
        return f" Совпадение: Текст: {text_match}, Баркоды: {barcode_match}, Позиции: {position_match}"

    def save_reference(self, file_name="reference.json"):
        file_path = os.path.join(self.reference_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.extracted_data, f, ensure_ascii=False, indent=4)
        print(f"\n Эталон сохранен: {file_path}")

    def delete_reference(self):
        for file in os.listdir(self.reference_dir):
            os.remove(os.path.join(self.reference_dir, file))
        print("\n Все эталоны удалены!")

    def find_pdf_files(self, directory):
        return [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]

    def process(self):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_files = self.find_pdf_files(project_dir)

        if self.expected_structure:
            print("\nℹ Найден эталонный файл.")
            choice = input("Удалить эталон (1) или оставить (2)? Введите 1 или 2: ").strip()
            if choice == "1":
                self.delete_reference()
                return
        else:
            print("\n Эталон отсутствует! Без него проверка невозможна.")
            if not pdf_files:
                print("В папке нет PDF-файлов. Добавьте файлы и запустите скрипт снова.")
                return

            print("\nВыберите PDF для создания эталона:")
            for idx, pdf_file in enumerate(pdf_files, start=1):
                print(f"{idx}. {pdf_file}")
            
            try:
                file_choice = int(input("\nВведите номер файла: "))
                file_path = os.path.join(project_dir, pdf_files[file_choice - 1])
                self.extract_data(file_path)
                self.save_reference()
                return
            except ValueError:
                print("\n Ошибка: некорректный ввод.")
                return

        if pdf_files:
            print("\nВыберите PDF для проверки:")
            for idx, pdf_file in enumerate(pdf_files, start=1):
                print(f"{idx}. {pdf_file}")
            try:
                file_choice = int(input("\nВведите номер файла: "))
                file_path = os.path.join(project_dir, pdf_files[file_choice - 1])
                self.extract_data(file_path)
                print("\n Итоговая проверка:", self.validate())
            except ValueError:
                print("\n Ошибка: некорректный ввод.")
        else:
            print("\n В папке проекта нет PDF-файлов.")

if __name__ == "__main__":
    processor = PDFProcessor()
    processor.process()
