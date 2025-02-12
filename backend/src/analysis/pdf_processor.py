import logging
from pathlib import Path
from typing import List
import pdf2image
from PIL import Image
import os
from backend.src.utils.config import config
from backend.src.analysis.image_analyzer import ImageAnalyzer

__all__ = ['process_pdf']

def process_pdf(pdf_path):
    processor = PDFProcessor()
    return processor.process_pdf(pdf_path)

class PDFProcessor:
    """
    Класс для обработки PDF файлов и конвертации их в изображения
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = Path(config.TEMP_DIR)
        self.output_dir = Path(os.path.join('backend', 'output'))
        self.slides_dir = self.output_dir / 'slides'
        self.max_file_size = config.max_file_size_bytes
        self.jpeg_quality = config.JPEG_QUALITY
        self.image_analyzer = ImageAnalyzer()
        
        # Создаем необходимые директории
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.slides_dir.mkdir(parents=True, exist_ok=True)
        
        # Параметры для обработки изображений
        self.max_resolution = (2000, 2000)
        self.current_pdf = None
        self.images = []
    
    def process_pdf(self, pdf_path: str | Path) -> List[Path]:
        """Обработка PDF файла и конвертация страниц в изображения"""
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"Файл не найден: {pdf_path}")
            
            # Очищаем старые файлы
            for old_file in self.slides_dir.glob("*.png"):
                old_file.unlink()
            
            # Конвертируем PDF в изображения
            images = pdf2image.convert_from_path(str(pdf_path))
            processed_images = []
            
            for idx, image in enumerate(images, 1):
                # Сохраняем изображение
                output_path = self.slides_dir / f"slide_{idx}.png"
                
                # Изменяем размер если необходимо
                if image.size[0] > self.max_resolution[0] or image.size[1] > self.max_resolution[1]:
                    image.thumbnail(self.max_resolution, Image.Resampling.LANCZOS)
                
                image.save(str(output_path), "PNG", optimize=True)
                processed_images.append(output_path)
                self.logger.info(f"Сохранен слайд {idx}: {output_path}")
                
                # Проверяем что файл действительно создан
                if not output_path.exists():
                    raise FileNotFoundError(f"Не удалось сохранить файл: {output_path}")
            
            # Сохраняем список обработанных изображений
            self.images = processed_images
            return processed_images
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке PDF: {str(e)}")
            raise
    
    def _process_image(self, image: Image.Image, idx: int) -> Path:
        """Обработка отдельного изображения"""
        # Изменяем размер если необходимо
        image = self._resize_image(image)
        
        # Сохраняем как PNG для лучшего качества
        output_path = self.slides_dir / f"slide_{idx:03d}.png"
        image.save(
            str(output_path),
            "PNG",
            optimize=True
        )
        
        return output_path
    
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Изменение размера изображения с сохранением пропорций"""
        if image.size[0] > self.max_resolution[0] or image.size[1] > self.max_resolution[1]:
            image.thumbnail(self.max_resolution, Image.Resampling.LANCZOS)
        return image
    
    def _check_file_size(self, file_path: Path) -> bool:
        """Проверка размера файла"""
        return file_path.stat().st_size <= self.max_file_size
    
    def cleanup(self):
        """Очистка временных файлов"""
        try:
            # Очищаем временную директорию
            for file in self.temp_dir.glob("*"):
                if file.name != ".gitkeep":
                    file.unlink()
            
            self.logger.info("Временные файлы успешно очищены")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке временных файлов: {str(e)}")

    def get_slide_image(self, slide_index: int) -> Path:
        """Получение изображения конкретного слайда"""
        if not self.current_pdf or slide_index < 0 or slide_index >= len(self.images):
            raise ValueError("Неверный индекс слайда или PDF не загружен")
        
        return self.images[slide_index]

    def process_slides(self, pdf_path):
        """Обработка и анализ всех слайдов"""
        self.logger.info(f"Начинаем обработку PDF: {pdf_path}")
        
        # Сначала обрабатываем PDF в изображения
        processed_images = self.process_pdf(pdf_path)
        results = []
        
        if not processed_images:
            self.logger.error("Не удалось получить изображения из PDF")
            return []
        
        self.logger.info(f"Получено {len(processed_images)} изображений для анализа")
        
        for i, image_path in enumerate(processed_images, 1):
            try:
                self.logger.info(f"Обработка слайда {i}/{len(processed_images)}: {image_path}")
                
                # Анализируем изображение
                analysis = self.image_analyzer.analyze_image(str(image_path))
                
                if analysis:
                    result = {
                        'slide_number': i,
                        'analysis': analysis,
                        'image_path': f"slides/slide_{i}.png"
                    }
                    results.append(result)
                    self.logger.info(f"Слайд {i} успешно проанализирован")
                else:
                    self.logger.warning(f"Пустой результат анализа для слайда {i}")
                    # Добавляем заглушку для сохранения последовательности
                    results.append({
                        'slide_number': i,
                        'analysis': "Не удалось проанализировать слайд",
                        'image_path': f"slides/slide_{i}.png"
                    })
                    
            except Exception as e:
                self.logger.error(f"Ошибка при обработке слайда {i}: {str(e)}")
                # Добавляем информацию об ошибке в результаты
                results.append({
                    'slide_number': i,
                    'analysis': f"Ошибка при анализе: {str(e)}",
                    'image_path': f"slides/slide_{i}.png"
                })
        
        self.logger.info(f"Обработано слайдов: {len(processed_images)}, получено результатов: {len(results)}")
        
        # Проверяем соответствие количества результатов и слайдов
        if len(results) != len(processed_images):
            self.logger.error(f"Несоответствие количества результатов ({len(results)}) и слайдов ({len(processed_images)})")
        
        return results
