import logging
from pathlib import Path
from typing import List, Dict, Any
import base64
from openai import OpenAI
from utils.config import config

class ImageAnalyzer:
    """
    Класс для анализа изображений с использованием OpenAI Vision API
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI()  # Автоматически использует OPENAI_API_KEY из окружения
        
        # Параметры для API запросов
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.MAX_TOKENS
        
        # Контекст анализа
        self.analysis_context = {
            'design_systems': [],    # Системы дизайна
            'variants': {},          # Варианты решений
            'elements': {},          # Элементы и свойства
            'slides_map': {}         # Карта связей
        }
    
    def analyze_slides(self, image_paths: List[Path]) -> Dict[str, Any]:
        """
        Анализ набора слайдов
        
        Args:
            image_paths: Список путей к изображениям слайдов
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        try:
            results = []
            for idx, image_path in enumerate(image_paths):
                self.logger.info(f"Анализ слайда {idx + 1}/{len(image_paths)}")
                slide_analysis = self._analyze_single_slide(image_path)
                results.append(slide_analysis)
                self._update_context(slide_analysis)
            
            return self._generate_final_report(results)
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе слайдов: {str(e)}")
            raise
    
    def _analyze_single_slide(self, image_path: Path) -> Dict[str, Any]:
        """Анализ отдельного слайда"""
        try:
            # Кодируем изображение в base64
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Формируем промпт с учетом контекста
            prompt = self._generate_analysis_prompt()
            
            # Отправляем запрос в OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens
            )
            
            # Обрабатываем ответ
            analysis_result = self._process_api_response(response)
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе слайда {image_path}: {str(e)}")
            raise
    
    def _generate_analysis_prompt(self) -> str:
        """Генерация промпта для анализа с учетом контекста"""
        return """Проанализируйте этот слайд брендбука и определите:
1. Основные элементы дизайн-системы
2. Цветовые решения и их значение
3. Типографику и её роль
4. Композиционные решения
5. Связи с предыдущими элементами дизайн-системы

Текущий контекст анализа:
{}""".format(str(self.analysis_context))
    
    def _process_api_response(self, response) -> Dict[str, Any]:
        """Обработка ответа от API"""
        try:
            content = response.choices[0].message.content
            # TODO: Структурировать ответ API
            return {
                "raw_analysis": content,
                "structured_data": self._structure_analysis(content)
            }
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ответа API: {str(e)}")
            raise
    
    def _structure_analysis(self, content: str) -> Dict[str, Any]:
        """Структурирование текстового анализа"""
        # TODO: Реализовать структурирование анализа
        return {"raw_content": content}
    
    def _update_context(self, slide_analysis: Dict[str, Any]):
        """Обновление контекста анализа"""
        # TODO: Реализовать обновление контекста
        pass
    
    def _generate_final_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Генерация финального отчета"""
        return {
            "slides_analysis": results,
            "context": self.analysis_context,
            # TODO: Добавить общие выводы и рекомендации
        } 