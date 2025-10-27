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
    gitlab_headers = {
        "PRIVATE-TOKEN": "zLZNJA6PjzudxPEfw2Ui"
    }
    list_services = ["GitLab Branch", "GitLab Issues", "GitLab Group", "GitLab Project", "GitLab Repository"]
    service = "GitLab Branch"
            
    generator = TestCaseGenerator(
        service_name=service,
        collection="Default",
        save_prompts=True,
        regenerate_test_data=True,  # Force regenerate với prompt mới
        data_generation_mode="all",
        clear_test_cases=True,  # Không xóa test cases khi chỉ generate test data
        headers=gitlab_headers
    )
    generator.generate_test_cases()
    generator.generate_test_data_for(generator.get_endpoints())
    # for service in list_services:
        
    #     generator = TestCaseGenerator(
    #         service_name=service,
    #         collection="Default",
    #         save_prompts=True,
    #         regenerate_test_data=True,  # Force regenerate với prompt mới
    #         data_generation_mode="all",
    #         clear_test_cases=False,  # Không xóa test cases khi chỉ generate test data
    #         headers=gitlab_headers
    #     )
    #     generator.generate_test_cases()
    #     generator.generate_test_data_for(generator.get_endpoints())

   
    print("✅ Generator completed successfully!")

    
except Exception as e:
    print(f"❌ Error occurred: {e}")
    logging.error(f"Error in run_generator.py: {e}", exc_info=True)
    sys.exit(1) 