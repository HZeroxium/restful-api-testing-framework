# main.py
from datetime import datetime
from sequence_runner.runner import SequenceRunner
import os
# if __name__ == "__main__":
#     # sequence_runner = SequenceRunner(service_name="Bill", base_url="https://bills-api.parliament.uk", token=None)

#     headers = {
#         "PRIVATE-TOKEN": "glpat-StZArnyBReXqgPkznx-c"
#     }
#     # endpoint = "_projects_id_protected_branches_POST_1_1"
#     # endpoint = "_projects_id_protected_branches_POST_1_1"
#     sequence_runner = SequenceRunner(service_name="GitLab Branch", base_url="http://localhost:30000/api/v4", token=None,out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}", headers=headers, endpoint=endpoint)
#     sequence_runner.run_all()

dir = "/Users/npt/Documents/NCKH/restful-api-testing-framework/src/database/Bill/test_cases"

def load_test_cases_from_dir(dir_path: str) -> list[str]:
    test_case_files = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".json") or file.endswith(".yaml") or file.endswith(".yml"):
                full_path = os.path.join(root, file)
                filename_no_ext = os.path.splitext(os.path.basename(full_path))[0]
                test_case_files.append(filename_no_ext)
    return test_case_files


if __name__ == "__main__":
    # sequence_runner = SequenceRunner(service_name="Bill", base_url="https://bills-api.parliament.uk", token=None)

    # headers = {
    #     "PRIVATE-TOKEN": "glpat-StZArnyBReXqgPkznx-c"
    # }   
    headers = {
        "PRIVATE-TOKEN": "zLZNJA6PjzudxPEfw2Ui"
    }
    # _api_v1_Bills_billId_NewsArticles_GetNewsArticles_2_1	
    # _api_v1_Bills_billId_Stages_GET_1_1	
    # list_endpoints = load_test_cases_from_dir(dir)
    # pop_endpoints = ["_api_v1_Bills_billId_Stages_billStageId_Amendments_amendmentId__GetAmendment_1_1", "_api_v1_Bills_billId_Stages_billStageId_Amendments_amendmentId__GetAmendment_0_1"]
    # list_endpoints = [ep for ep in list_endpoints if ep not in pop_endpoints]

    # endpoint = None
    sequence_runner = SequenceRunner(service_name="Canada Holidays",skip_preload=True, base_url="https://canada-holidays.ca", token=None,out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}", headers=headers)
    sequence_runner.run_all()