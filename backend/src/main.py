import logging
from pathlib import Path
from analysis.pdf_processor import PDFProcessor
from analysis.image_analyzer import ImageAnalyzer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Инициализация процессоров
    pdf_processor = PDFProcessor()
    image_analyzer = ImageAnalyzer()
    
    # Путь к тестовому PDF
    test_pdf = "/Users/l-tune/APPS/DesignAnalyzer/IDENTITY TEST.pdf"
    
    try:
        # Конвертация PDF в изображения
        print("Шаг 1: Конвертация PDF в изображения")
        image_paths = pdf_processor.process_pdf(test_pdf)
        print(f"Создано {len(image_paths)} изображений\n")
        
        # Анализ изображений
        print("Шаг 2: Анализ изображений")
        analysis_results = image_analyzer.analyze_slides(image_paths)
        
        # Вывод результатов
        print("\nРезультаты анализа:")
        for idx, result in enumerate(analysis_results['slides_analysis']):
            print(f"\nСлайд {idx + 1}:")
            print(result['raw_analysis'])
            
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
    finally:
        pdf_processor.cleanup()

if __name__ == "__main__":
    main()
