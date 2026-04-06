import hashlib
import os
import logging
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pillow_heif
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session
from sqlalchemy import and_, String
from src.app.models import FuelOperation
from src.ocr.schemas import ReceiptData
from src.app.db import get_db_session

pillow_heif.register_heif_opener()
load_dotenv()


class SmartFuelOCR:
    def __init__(self, db_session: Session, model_name: str = "qwen/qwen3.6-plus:free"):
        self.db = db_session
        self.setup_logging()

        self.llm = ChatOpenAI(
            model=model_name,
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            temperature=0
        )
        self.parser = PydanticOutputParser(pydantic_object=ReceiptData)
        pytesseract.pytesseract.tesseract_cmd = r'E:\programs\tesseract.exe'

    def setup_logging(self):
        """Настройка журналирования в файл и консоль"""
        self.logger = logging.getLogger("SmartFuelOCR")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            file_h = logging.FileHandler("ocr_processing.log", encoding="utf-8")
            file_h.setFormatter(formatter)

            cons_h = logging.StreamHandler()
            cons_h.setFormatter(formatter)

            self.logger.addHandler(file_h)
            self.logger.addHandler(cons_h)

    def _get_image_hash(self, image_path: str)-> str:
        """Хэш изображения для защиты от повторной загрузки того же файла"""
        with open(image_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()


    def load_and_convert_image(self, image_path: str) -> np.ndarray:
        """Загрузка изображения любого формата и конвертация в OpenCV формат"""
        path = Path(image_path)
        pil_img = Image.open(path).convert('RGB')
        open_cv_image = np.array(pil_img)
        open_cv_image = open_cv_image[:, :, ::-1].copy()

        return open_cv_image

    def preprocess(self, img: np.ndarray) -> np.ndarray:
        """Предобработка изображения"""
        h, w = img.shape[:2]
        ratio = 1500 / w
        img = cv2.resize(img, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(10, 10))
        gray = clahe.apply(gray)

        gaussian_3 = cv2.GaussianBlur(gray, (0, 0), 3)
        gray = cv2.addWeighted(gray, 1.5, gaussian_3, -0.5, 0)

        final = cv2.bilateralFilter(gray, 9, 75, 75)
        _, thresh = cv2.threshold(final, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return thresh

    def _check_duplicates(self, img_hash: str, structured_data: ReceiptData):
        """
        Проверка уникальности по двум критериям:
        1. Хэш файла
        2. Бизнес-данные (Номер чека + Дата + Кол-во)
        """
        # Проверка хэша в JSON поле ocr_data
        duplicate_hash = self.db.query(FuelOperation).filter(
            FuelOperation.ocr_data['image_hash'].cast(String) == img_hash
        ).first()

        if duplicate_hash:
            return True, f"Файл с хэшем {img_hash} уже обрабатывался (ID: {duplicate_hash.id})"

        # Проверка бизнес-логики (Номер чека, Дата, Количество)
        try:
            # Превращаем строку даты/времени из OCR в объект datetime для сравнения
            # В ReceiptData должны быть поля date, time, quantity, receipt_number
            dt_str = f"{structured_data.date} {structured_data.time}"
            dt_obj = datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")  # Формат зависит от вашего ReceiptData
        except (ValueError, TypeError):
            dt_obj = None

        duplicate_biz = self.db.query(FuelOperation).filter(
            and_(
                FuelOperation.doc_number == structured_data.doc_number,
                FuelOperation.date_time == dt_obj,
                FuelOperation.ocr_data['quantity'].cast(String) == str(structured_data.quantity)
            )
        ).first()

        if duplicate_biz:
            return True, f"Чек №{structured_data.doc_number} от {dt_obj} уже существует (ID: {duplicate_biz.id})"

        return False, ""

    def extract_raw_text(self, processed_img: np.ndarray) -> str:
        """Извлечение текста через Tesseract"""
        config = "--psm 6 -l rus+eng"
        return pytesseract.image_to_string(processed_img, config=config)

    def structure_with_llm(self, raw_text: str) -> ReceiptData:
        """Использование агента для парсинга и исправления ошибок"""
        prompt = ChatPromptTemplate.from_template(
            "Вы — эксперт по анализу кассовых чеков АЗС.\n"
            "Ниже приведен текст, полученный после OCR распознавания. "
            "В тексте могут быть ошибки распознавания символов. Исправьте их логически.\n"
            "Извлеките данные в строго структурированном виде.\n"
            "Верните дату строго в формате ДД.ММ.ГГГГ.\n"
            "Верните время строго в формате ЧЧ:ММ:СС.\n"
            "Если данных нет, верните null.\n\n"
            "Текст чека:\n{raw_text}\n\n"
            "{format_instructions}"
        )
        chain = prompt | self.llm | self.parser

        return chain.invoke({
            "raw_text": raw_text,
            "format_instructions": self.parser.get_format_instructions()
        })

    def run_pipeline(self, image_path: str, telegram_user_id: int = None):
        self.logger.info(f"Начало обработки: {image_path}")

        img_hash = self._get_image_hash(image_path)

        try:
            img = self.load_and_convert_image(image_path)
            processed_img = self.preprocess(img)
            raw_text = self.extract_raw_text(processed_img)

            self.logger.info("Текст извлечен, отправка в LLM...")
            structured_data = self.structure_with_llm(raw_text)

            if not structured_data:
                self.logger.error("LLM не смогла распознать структуру чека.")
                return None
        except Exception as e:
            self.logger.error(f"Критическая ошибка OCR: {e}")
            return None

        is_dup, reason = self._check_duplicates(img_hash, structured_data)
        if is_dup:
            self.logger.warning(f"Отказ в регистрации: {reason}")
            return {"status": "duplicate", "message": reason}

        # Сохранение в БД
        try:
            # Готовим данные для колонки ocr_data
            full_ocr_json = structured_data.model_dump()
            full_ocr_json['image_hash'] = img_hash
            full_ocr_json['raw_text_debug'] = raw_text

            new_op = FuelOperation(
                source='personal_receipt',
                ocr_data=full_ocr_json,
                doc_number=structured_data.doc_number,
                # Преобразуем дату для колонки date_time
                date_time=datetime.strptime(f"{structured_data.date} {structured_data.time}", "%d.%m.%Y %H:%M:%S"),
                status="new",
                imported_at=datetime.now(timezone.utc)
            )

            self.db.add(new_op)
            self.db.flush()  # Получаем ID операции

            self.logger.info(f"Операция успешно создана. ID: {new_op.id}")
            self.db.commit()
            return full_ocr_json

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Ошибка сохранения в БД: {e}")
            return None


# if __name__ == "__main__":
#     from contextlib import contextmanager
#
#     with get_db_session() as session:
#         processor = SmartFuelOCR(session)
#
#         res = processor.run_pipeline(
#             r"D:/Хакатоны/Хакатон Смарт Агро/test_1.jpg"
#         )
#
#         print(json.dumps(res, indent=4, ensure_ascii=False))
#
