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
    from kat.test_case_generator.test_case_generator import TestCaseGenerator
    
    # Khởi tạo generator với service name và collection name
    generator = TestCaseGenerator(
        service_name="GitLab Branch",  # Sửa tên từ "Bil" thành "Bill" để match với thư mục Dataset
        collection="Default",    # Tên collection mặc định
        save_prompts=True,
        regenerate_test_data=False,
        data_generation_mode="all"
    )
    
    # Chạy generator

    
    result = generator.run()
    
    print("✅ Generator completed successfully!")

    
except Exception as e:
    print(f"❌ Error occurred: {e}")
    logging.error(f"Error in run_generator.py: {e}", exc_info=True)
    sys.exit(1) 