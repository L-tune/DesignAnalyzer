import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """
    Класс конфигурации приложения
    """
    def __init__(self):
        # Загружаем переменные окружения
        load_dotenv()
        
        # Базовые директории
        self.TEMP_DIR = Path(os.getenv('TEMP_DIR', 'backend/temp'))
        self.OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'backend/output'))
        self.SLIDES_DIR = Path(os.getenv('SLIDES_DIR', 'backend/slides_images'))
        
        # Ограничения для обработки файлов
        self.MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 50))
        self.JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', 90))
        
        # OpenAI настройки
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.MAX_TOKENS = int(os.getenv('MAX_TOKENS', 4096))
        
        # Создаем директории если они не существуют
        self._create_directories()
    
    def _create_directories(self):
        """Создание необходимых директорий"""
        for directory in [self.TEMP_DIR, self.OUTPUT_DIR, self.SLIDES_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def max_file_size_bytes(self) -> int:
        """Максимальный размер файла в байтах"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

# Создаем глобальный экземпляр конфигурации
config = Config()
