import os

import cv2
import numpy as np
import pytesseract
import hashlib
from pathlib import Path
from PIL import Image
import pillow_heif
from typing import Optional, List
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from src.ocr.schemas import ReceiptData

pillow_heif.register_heif_opener()
load_dotenv()


class SmartFuelOCR:
    def __init__(self, model_name: str = "openrouter/hunter-alpha"):
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            temperature=0
        )
        self.parser = PydanticOutputParser(pydantic_object=ReceiptData)
        pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'

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
            "Если данных нет, верните null.\n\n"
            "Текст чека:\n{raw_text}\n\n"
            "{format_instructions}"
        )
        chain = prompt | self.llm | self.parser

        return chain.invoke({
            "raw_text": raw_text,
            "format_instructions": self.parser.get_format_instructions()
        })

    def run_pipeline(self, image_path: str):
        print(f"Начало обработки: {image_path}")

        img = self.load_and_convert_image(image_path)
        processed_img = self.preprocess(img)
        raw_text = self.extract_raw_text(processed_img)

        print("Текст успешно считан, отправка в LLM...")

        structured_data = self.structure_with_llm(raw_text)
        result_dict = structured_data.model_dump()
        with open(image_path, "rb") as f:
            result_dict["image_path"] = hashlib.md5(f.read()).hexdigest()

        return result_dict


if __name__ == "__main__":
    processor = SmartFuelOCR()

    res = processor.run_pipeline(r"D:/Хакатоны/Хакатон Смарт Агро/test_2.jpg")
    import json

    print(json.dumps(res, indent=4, ensure_ascii=False))
