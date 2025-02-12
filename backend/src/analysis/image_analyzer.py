import logging
from pathlib import Path
from typing import List, Dict, Any, Set
import base64
from openai import OpenAI
from backend.src.utils.config import config

__all__ = ['analyze_image']

def analyze_image(img, context):
    analyzer = ImageAnalyzer()
    analyzer.initialize_context(context, 1)  # Один слайд
    return analyzer._analyze_single_slide(img, 1)  # Передаем номер слайда

class ImageAnalyzer:
    """
    Класс для анализа изображений презентации с учетом контекста
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI()
        
        # Параметры для API запросов
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.MAX_TOKENS
        
        # Контекст презентации
        self.presentation_context = {
            'general_context': '',      # Общий контекст из вводного поля
            'total_slides': 0,          # Общее количество слайдов
            'current_themes': set(),    # Текущие темы презентации
            'key_concepts': set()       # Ключевые концепции
        }
        
        # Добавляем атрибут для хранения текущих изображений
        self.current_images = []
    
    def initialize_context(self, context: str, total_slides: int):
        """Инициализация контекста презентации"""
        self.presentation_context['general_context'] = context
        self.presentation_context['total_slides'] = total_slides
        self.presentation_context['current_themes'] = set()
        self.presentation_context['key_concepts'] = set()
        self.logger.info(f"Инициализирован контекст презентации. Всего слайдов: {total_slides}")
    
    def _analyze_single_slide(self, image_path: Path, slide_number: int) -> str:
        """Анализ одного слайда с учетом контекста"""
        try:
            self.logger.info(f"Начинаем анализ слайда {slide_number}")
            
            # Кодируем изображение в base64
            with open(image_path, 'rb') as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Формируем промпт с учетом контекста
            context = self.presentation_context['general_context'] or "общая аудитория"
            prompt = f"""Вы объясняете содержимое слайда для следующей аудитории: {context}

Проанализируйте слайд {slide_number} из {self.presentation_context['total_slides']}.

Используйте язык и термины, понятные указанной аудитории. Ответ дайте строго в следующем формате:

СУТЬ
Краткое и понятное описание того, что показано на слайде.

ТЕЗИСЫ
- Первый важный момент
- Второй важный момент
- Третий важный момент

АКЦЕНТЫ
Ключевые слова через запятую. Важные слова выделите тегами <blue>слово</blue>."""

            # Запрос к API
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
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens
            )
            
            if not response.choices:
                raise ValueError("Пустой ответ от API")
            
            analysis = response.choices[0].message.content
            if not analysis:
                raise ValueError("Пустой анализ от API")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе слайда: {str(e)}", exc_info=True)
            raise
    
    def _generate_analysis_prompt(self, slide_number: int) -> str:
        """Генерация промпта для анализа с учетом контекста"""
        context = self.presentation_context
        return f"""Проанализируйте слайд {slide_number} из {context['total_slides']}.
Контекст аудитории: {context['general_context']}

Представьте анализ в следующем формате:

СУТЬ
Краткое описание главной идеи слайда в 2-3 предложениях.

ТЕЗИСЫ
- Первый ключевой тезис
- Второй ключевой тезис
- Третий ключевой тезис

АКЦЕНТЫ
Ключевые слова и фразы для презентации, разделенные запятыми. Самые важные слова выделить (!) восклицательным знаком.

Важно:
- Строго соблюдать структуру разделов
- Использовать четкие и лаконичные формулировки
- Выделять ключевые слова знаком (!)
- Адаптировать язык под аудиторию"""

    def _update_context_from_analysis(self, analysis: str):
        """Обновление контекста на основе анализа слайда"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": f"""
Представьте, что вы часть этой аудитории: {self.presentation_context['general_context']}

Что для них реально важно в этом объяснении? 
Какие темы и идеи они бы выделили, используя свой язык?

Верните строго в формате:
Темы: тема1, тема2
Концепции: концепция1, концепция2

Текст: {analysis}

Важно:
- Использовать их реальный язык и выражения
- Выделять то, что важно именно для них
- Сохранять их настоящий стиль общения"""
                }],
                max_tokens=100
            )
            
            if not response.choices or not response.choices[0].message.content:
                self.logger.warning("Пустой ответ при извлечении контекста")
                return
            
            # Парсим ответ
            result = response.choices[0].message.content
            
            # Извлекаем темы и концепции
            themes = set()
            concepts = set()
            
            for line in result.split('\n'):
                if line.startswith('Темы:'):
                    themes = {theme.strip() for theme in line.replace('Темы:', '').split(',') if theme.strip()}
                elif line.startswith('Концепции:'):
                    concepts = {concept.strip() for concept in line.replace('Концепции:', '').split(',') if concept.strip()}
            
            # Обновляем контекст
            self.presentation_context['current_themes'].update(themes)
            self.presentation_context['key_concepts'].update(concepts)
            
            self.logger.debug(f"Обновлен контекст: темы={themes}, концепции={concepts}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении контекста: {str(e)}", exc_info=True)
    
    def analyze_slides(self, image_paths: List[Path]) -> Dict[str, Any]:
        """Анализ набора слайдов"""
        try:
            # Сохраняем текущие изображения
            self.current_images = image_paths
            self.logger.info(f"Начинаем анализ {len(image_paths)} слайдов")
            
            results = []
            for idx, image_path in enumerate(image_paths, 1):
                self.logger.info(f"Обработка слайда {idx}/{len(image_paths)}: {image_path}")
                try:
                    slide_analysis = self._analyze_single_slide(image_path, idx)
                    self.logger.info(f"Получен анализ для слайда {idx}: {slide_analysis[:100]}...")
                    
                    results.append({
                        'slide_number': idx,
                        'analysis': slide_analysis
                    })
                except Exception as e:
                    self.logger.error(f"Ошибка при анализе слайда {idx}: {str(e)}")
                    # Добавляем заглушку для сохранения нумерации
                    results.append({
                        'slide_number': idx,
                        'analysis': f"""
СУТЬ
Ошибка при анализе слайда

ТЕЗИСЫ
- Не удалось проанализировать слайд
- Пожалуйста, попробуйте повторить анализ

АКЦЕНТЫ
ошибка (!), повторить анализ (!)
"""
                    })
            
            self.logger.info(f"Завершен анализ всех слайдов. Всего результатов: {len(results)}")
            
            # Проверяем, что количество результатов совпадает с количеством слайдов
            if len(results) != len(image_paths):
                self.logger.error(f"Несоответствие количества результатов ({len(results)}) и слайдов ({len(image_paths)})")
            
            context_for_json = {
                'general_context': self.presentation_context['general_context'],
                'total_slides': self.presentation_context['total_slides'],
                'current_themes': list(self.presentation_context['current_themes']),
                'key_concepts': list(self.presentation_context['key_concepts'])
            }
            
            return {
                'slides_analysis': results,
                'context': context_for_json
            }
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка при анализе слайдов: {str(e)}", exc_info=True)
            raise
    
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
    
    def _generate_final_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Генерация финального отчета"""
        return {
            "slides_analysis": results,
            "context": self.presentation_context,
            # TODO: Добавить общие выводы и рекомендации
        }
    
    def get_current_images(self) -> List[Path]:
        """Получение текущего набора обрабатываемых изображений"""
        return self.current_images

    def analyze_image(self, image_path):
        try:
            self.logger.info(f"Анализ изображения: {image_path}")
            
            # Загружаем изображение
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Формируем запрос к API в правильном формате
            messages = [
                {"role": "system", "content": "Вы - эксперт по анализу дизайна и визуальных материалов."},
                {"role": "user", "content": [
                    {"type": "text", "text": """Проанализируйте этот слайд и опишите его содержание в следующем формате:

СУТЬ
Краткое описание того, что показано на слайде.

ТЕЗИСЫ
- Первый важный момент
- Второй важный момент
- Третий важный момент

АКЦЕНТЫ
Ключевые слова через запятую"""},
                    {"type": "image_url", 
                     "image_url": {
                         "url": f"data:image/png;base64,{image_data}",
                         "detail": "high"
                     }
                    }
                ]}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )
            
            analysis = response.choices[0].message.content
            if analysis:
                self.logger.info(f"Получен анализ длиной {len(analysis)} символов")
            else:
                self.logger.warning("Получен пустой анализ")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе изображения: {str(e)}")
            return None 