from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import sys
from typing import Optional
import logging

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
import json
from dotenv import load_dotenv
from backend.src.utils.config import config

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['UPLOAD_FOLDER'] = 'uploads'

logger.info(f"Инициализация приложения. Upload folder: {app.config['UPLOAD_FOLDER']}")

# Создаем папку для загрузок, если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Создаем экземпляры классов
pdf_processor = PDFProcessor()
image_analyzer = ImageAnalyzer()

@app.route('/')
def index():
    logger.debug("Запрошена главная страница")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("Получен запрос на загрузку файла")
        logger.debug(f"Files в запросе: {request.files}")
        logger.debug(f"Headers: {request.headers}")
        
        if 'files[]' not in request.files:
            logger.warning("Файл не найден в запросе")
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['files[]']
        logger.info(f"Получен файл: {file.filename}")
        logger.debug(f"Тип файла: {file.content_type}")
        
        if not file or not file.filename:
            logger.warning("Пустое имя файла")
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Неверный формат файла: {file.filename}")
            return jsonify({'error': 'Разрешены только PDF файлы'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.info(f"Сохраняем файл: {filepath}")
        
        file.save(filepath)
        logger.info("Файл успешно сохранен")
        
        response_data = {
            'message': 'Файл успешно загружен',
            'filename': filename,
            'filepath': filepath
        }
        logger.debug(f"Отправляем ответ: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}", exc_info=True)
        return jsonify({'error': f'Ошибка при загрузке: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze_pdf():
    try:
        logger.info("Получен запрос на анализ PDF")
        data = request.get_json()
        logger.debug(f"Полученные данные: {data}")
        
        if not data:
            logger.warning("Данные не получены")
            return jsonify({'error': 'Данные не получены'}), 400
            
        filepath = data.get('filepath', '')
        context = data.get('context', '')
        logger.info(f"Анализируем файл: {filepath}")
        logger.debug(f"Контекст: {context}")
        
        if not filepath or not os.path.exists(filepath):
            logger.warning(f"Файл не найден: {filepath}")
            return jsonify({'error': 'Файл не найден'}), 404

        # Используем методы классов
        logger.info("Начинаем обработку PDF")
        try:
            images = pdf_processor.process_pdf(filepath)
            logger.info(f"PDF успешно обработан, получено {len(images)} изображений")
            logger.debug(f"Пути к изображениям: {images}")
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF: {str(e)}", exc_info=True)
            return jsonify({'error': 'Ошибка при обработке PDF'}), 500
        
        results = []
        for idx, img in enumerate(images):
            logger.info(f"Анализируем слайд {idx + 1}/{len(images)}")
            try:
                analysis = image_analyzer._analyze_single_slide(img)
                logger.debug(f"Результат анализа слайда {idx + 1}: {analysis[:100]}...")
                results.append({
                    'slide_number': idx + 1,
                    'analysis': analysis
                })
            except Exception as e:
                logger.error(f"Ошибка при анализе слайда {idx + 1}: {str(e)}", exc_info=True)
                return jsonify({'error': f'Ошибка при анализе слайда {idx + 1}'}), 500

        logger.info("Анализ завершен успешно")
        response_data = {
            'success': True,
            'results': results
        }
        logger.debug(f"Отправляем результаты: {str(response_data)[:200]}...")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Ошибка при анализе PDF: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/test')
def test_upload():
    logger.debug("Запрошена тестовая страница загрузки")
    return render_template('test_upload.html')

@app.route('/slides/<path:filename>')
def serve_slide(filename):
    """Отдача изображений слайдов"""
    logger.debug(f"Запрошен слайд: {filename}")
    return send_from_directory(config.OUTPUT_DIR, filename)

if __name__ == '__main__':
    logger.info("Запуск приложения")
    app.run(debug=True) 