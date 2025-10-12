from operator import ge
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
        service_name="Pet Store",
        collection="Default",
        save_prompts=True,
        regenerate_test_data=False,  # Force regenerate với prompt mới
        data_generation_mode="all",
        clear_test_cases=False,  # Không xóa test cases khi chỉ generate test data
    )

    # generator.generate_test_data_for(generator.get_endpoints())
    generator.generate_test_cases()
    # generator = TestCaseGenerator(
    #     service_name="Bill",
    #     collection="Default",
    #     save_prompts=True,
    #     data_generation_mode="all"
    # )
    # generator.generate_test_data_for(generator.get_endpoints())

    # get-/api/v1/Bills
    # get-/api/v1/Bills/{billId}/NewsArticles	
    # Chạy generator - chỉ generate test data, không xóa test cases hiện có

    # generator.generate_test_data_for(generator.get_endpoints())
    # generator.generate_test_cases()
    print("✅ Generator completed successfully!")

    
except Exception as e:
    print(f"❌ Error occurred: {e}")
    logging.error(f"Error in run_generator.py: {e}", exc_info=True)
    sys.exit(1) 