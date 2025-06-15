import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('generator.log')
    ]
)

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🚀 Starting Test Case Generator")
print("=" * 60)

try:
    print("📦 Importing TestCaseGenerator...")
    from kat.test_case_generator.test_case_generator import TestCaseGenerator
    print("✅ Import successful!")
    
    # Khởi tạo generator với service name và collection name
    print("🔧 Initializing generator...")
    generator = TestCaseGenerator(
        service_name="Canada Holidays",  # Sửa tên từ "Canada Holiday" thành "Canada Holidays"
        collection="Default",    # Tên collection mặc định
        save_prompts=True,
        regenerate_test_data=False,
        data_generation_mode="all"
    )
    print("✅ Generator initialized successfully!")
    
    # Chạy generator
    print("🏃 Running generator...")
    print("This may take a few minutes, please wait...")
    
    result = generator.run()
    
    print("✅ Generator completed successfully!")
    print("📁 Check the output directory for generated test cases.")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error occurred: {e}")
    logging.error(f"Error in run_generator.py: {e}", exc_info=True)
    sys.exit(1) 