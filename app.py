from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import sys
from typing import Optional
import logging
import shutil
import json

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем путь к корневой директории проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.src.analysis.pdf_processor import PDFProcessor
from backend.src.analysis.image_analyzer import ImageAnalyzer
from dotenv import load_dotenv
from backend.src.utils.config import config

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SLIDES_FOLDER'] = os.path.join('backend', 'output', 'slides')  # Новая конфигурация

logger.info(f"Инициализация приложения. Upload folder: {app.config['UPLOAD_FOLDER']}")

# Создаем необходимые папки
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SLIDES_FOLDER'], exist_ok=True)

# Создаем экземпляры классов
pdf_processor = PDFProcessor()
image_analyzer = ImageAnalyzer()

@app.route('/')
def index():
    return render_template('test_upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Проверяем наличие файла
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    if not file or not file.filename:  # Проверяем filename перед использованием
        return jsonify({'error': 'Файл не выбран'}), 400

    filename = file.filename  # Сохраняем filename в переменную, т.к. знаем что он не None
    
    # Проверяем расширение
    allowed_extensions = {'.pdf', '.ppt', '.pptx'}
    file_ext = os.path.splitext(str(filename))[1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'Поддерживаются только файлы PDF, PPT и PPTX'}), 400

    try:
        # Сохраняем файл
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(filepath)

        # Получаем контекст
        context = request.form.get('context', '')

        # Здесь будет обработка через pdf_processor
        
        return jsonify({
            'success': True,
            'filename': filename,  # Возвращаем оригинальное имя файла
            'message': 'Файл успешно загружен'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        filename = data.get('filename')
        context = data.get('context', '')
        
        logger.info(f"Начинаем анализ файла: {filename}")
        
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Файл не найден'}), 404
        
        # Обработка PDF и сохранение слайдов
        logger.info("Извлечение слайдов из PDF")
        results = pdf_processor.process_slides(filepath)
        total_slides = len(results)
        logger.info(f"Извлечено {total_slides} слайдов")
        
        # Добавляем отладочный вывод
        logger.debug(f"Результаты анализа: {json.dumps(results, ensure_ascii=False)}")
        
        # Проверяем что все файлы на месте
        for i in range(1, total_slides + 1):
            slide_path = os.path.join(app.config['SLIDES_FOLDER'], f'slide_{i}.png')
            if not os.path.exists(slide_path):
                logger.error(f"Отсутствует файл слайда: {slide_path}")
                return jsonify({'error': 'Ошибка при сохранении слайдов'}), 500
        
        # Проверяем что все слайды имеют результаты
        for i, result in enumerate(results, 1):
            if not result.get('analysis'):
                logger.warning(f"Отсутствует анализ для слайда {i}")
        
        return jsonify({
            'success': True,
            'results': results,
            'context': context
        })

    except Exception as e:
        logger.error(f"Ошибка при анализе: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test_upload():
    logger.debug("Запрошена тестовая страница загрузки")
    return render_template('test_upload.html')

@app.route('/slides/<path:filename>')
def serve_slide(filename):
    """Отдача изображений слайдов"""
    try:
        if os.path.exists(app.config['SLIDES_FOLDER']):
            filepath = os.path.join(app.config['SLIDES_FOLDER'], filename)
            if os.path.exists(filepath):
                return send_from_directory(app.config['SLIDES_FOLDER'], filename)
        
        logger.error(f"Файл не найден: {filepath}")
        return "Изображение не найдено", 404
            
    except Exception as e:
        logger.error(f"Ошибка при отдаче слайда: {str(e)}")
        return str(e), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Очистка временных файлов при закрытии приложения"""
    try:
        # Очищаем только основную папку uploads от PDF файлов
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            if file.lower().endswith(('.pdf', '.ppt', '.pptx')):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла {file_path}: {e}")
        
        logger.info("Очистка временных файлов выполнена успешно")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при очистке временных файлов: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Запуск приложения")
    app.run(debug=True, port=5001) 