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

if __name__ == "__main__":
    # sequence_runner = SequenceRunner(service_name="Bill", base_url="https://bills-api.parliament.uk", token=None)

    # headers = {
    #     "PRIVATE-TOKEN": "glpat-StZArnyBReXqgPkznx-c"
    # }   
    headers = {
        "PRIVATE-TOKEN": "zLZNJA6PjzudxPEfw2Ui",
    }
    # _api_v1_Bills_billId_NewsArticles_GetNewsArticles_2_1	
    # _api_v1_Bills_billId_Stages_GET_1_1	
    # list_endpoints = load_test_cases_from_dir(dir)
    # pop_endpoints = ["_api_v1_Bills_billId_Stages_billStageId_Amendments_amendmentId__GetAmendment_1_1", "_api_v1_Bills_billId_Stages_billStageId_Amendments_amendmentId__GetAmendment_0_1"]
    # list_endpoints = [ep for ep in list_endpoints if ep not in pop_endpoints]

    # endpoint = None
    # sequence_runner = SequenceRunner(service_name="Gitlab Commit",skip_preload=True, base_url="http://localhost:30000/api/v4", token=None,out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}", headers=headers)

    # sequence_runner = SequenceRunner(service_name="Bill",skip_preload=True, base_url="https://bills-api.parliament.uk/", token=None,out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}", headers=headers)
    # sequence_runner = SequenceRunner(
    #     service_name="Pet Store",
    #     skip_preload=True,
    #     base_url="http://localhost:8081/api/v3",
    #     out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}",
    #     headers=headers,
    #     sampling_strategy="random_quota",
    #     want_2xx=3,
    #     want_4xx=10
    # )
    # sequence_runner.run_all()
    # endpoint = ["_groups_POST_0_1"]
    sequence_runner = SequenceRunner(
        service_name="GitLab Branch",
        skip_preload=False,
        base_url="http://localhost:30000/api/v4",
        out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}",
        headers=headers,
        sampling_strategy="random_quota",
        want_2xx=20,
        want_4xx=0,
        # endpoint=endpoint
    )
    sequence_runner.run_all()