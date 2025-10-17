# main.py
from datetime import datetime
from sequence_runner.runner import SequenceRunner

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
        "PRIVATE-TOKEN": "zLZNJA6PjzudxPEfw2Ui"
    }
    
    endpoint = "_api_v1_Bills_billId__GetBill_1_1"
    # endpoint = None
    sequence_runner = SequenceRunner(service_name="Bill", base_url="https://bills-api.parliament.uk", token=None,out_file_name=f"{datetime.now().strftime('%Y%m%d%H%M%S')}", headers=headers, endpoint=endpoint)
    sequence_runner.run_all()