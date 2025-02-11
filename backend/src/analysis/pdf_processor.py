import logging
from pathlib import Path
from typing import List
import pdf2image
from PIL import Image
import os
from utils.config import config

class PDFProcessor:
    """
    Класс для обработки PDF файлов и конвертации их в изображения
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = config.TEMP_DIR
        self.output_dir = config.OUTPUT_DIR
        self.max_file_size = config.max_file_size_bytes
        self.jpeg_quality = config.JPEG_QUALITY
        
        # Параметры для обработки изображений
        self.max_resolution = (2000, 2000)
    
    def process_pdf(self, pdf_path: str | Path) -> List[Path]:
        """
        Обработка PDF файла и конвертация страниц в изображения
        
        Args:
            pdf_path: Путь к PDF файлу
            
        Returns:
            List[Path]: Список путей к обработанным изображениям
            
        Raises:
            ValueError: Если файл превышает допустимый размер
            FileNotFoundError: Если файл не найден
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")
            
        if not self._check_file_size(pdf_path):
            raise ValueError(
                f"Файл превышает максимально допустимый размер "
                f"{self.max_file_size/1024/1024:.1f}MB"
            )
        
        try:
            # Конвертируем PDF в изображения
            images = pdf2image.convert_from_path(str(pdf_path))
            processed_images = []
            
            for idx, image in enumerate(images):
                processed_path = self._process_image(image, idx)
                processed_images.append(processed_path)
            
            self.logger.info(f"Успешно обработано {len(processed_images)} страниц из {pdf_path}")
            return processed_images
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке PDF: {str(e)}")
            raise
    
    def _process_image(self, image: Image.Image, idx: int) -> Path:
        """Обработка отдельного изображения"""
        # Изменяем размер если необходимо
        image = self._resize_image(image)
        
        # Сохраняем с оптимизацией
        output_path = self.output_dir / f"slide_{idx:03d}.jpg"
        image.save(
            output_path,
            "JPEG",
            quality=self.jpeg_quality,
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
            for file in self.temp_dir.glob("*"):
                if file.name != ".gitkeep":
                    file.unlink()
            self.logger.info("Временные файлы успешно очищены")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке временных файлов: {str(e)}")
