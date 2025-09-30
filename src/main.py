# main.py
from sequence_runner.runner import SequenceRunner

if __name__ == "__main__":
    # sequence_runner = SequenceRunner(service_name="Bill", base_url="https://bills-api.parliament.uk", token=None)
    sequence_runner = SequenceRunner(service_name="Canada Holidays", base_url="https://canada-holidays.ca", token=None)
    sequence_runner.run_all()