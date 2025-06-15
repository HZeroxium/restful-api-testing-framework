import os

WORKING_DIRECTORY = "./KAT_CLONE_TEST_CASES"

def get_output_dir(service_name, phase):
    return f"{WORKING_DIRECTORY}/{service_name}/{phase}/"

def get_data_dir_file(service_name):
    # Get the absolute path to the Dataset directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    return os.path.join(project_root, "Dataset", service_name, "openapi.json")

def get_odg_working_dir(service_name):
    return f"{WORKING_DIRECTORY}/{service_name}/ODG/"
def get_test_case_generator_working_dir(service_name):
    return f"{WORKING_DIRECTORY}/{service_name}/test_case_generator/"
def get_operation_sequences_file_path(service_name):
    return f"{get_odg_working_dir(service_name)}operation_sequences.json"
def get_endpoint_schema_dependencies_file_path(service_name):
    return f"{get_odg_working_dir(service_name)}endpoint_schema_dependencies.json"
def get_topolist_file_path(service_name):
    return f"{get_odg_working_dir(service_name)}topolist.json"
def get_test_data_working_dir(service_name):
    return f"{WORKING_DIRECTORY}/{service_name}/TestData/"
def get_root_dir():
    return f"{WORKING_DIRECTORY}/"