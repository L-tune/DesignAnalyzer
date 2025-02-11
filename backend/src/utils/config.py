import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    TEMP_DIR = Path(os.getenv('TEMP_DIR', 'backend/temp'))
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'backend/output'))
    SLIDES_DIR = Path(os.getenv('SLIDES_DIR', 'backend/slides_images'))
    
    max_file_size_bytes = int(os.getenv('MAX_FILE_SIZE_MB', 50)) * 1024 * 1024
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', 90))
    
    # OpenAI settings
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', 4096))

config = Config()
