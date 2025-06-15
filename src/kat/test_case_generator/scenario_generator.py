from kat.utils.llm.gpt.gpt import GPTChatCompletion


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def generate_basic_scenario(**kwargs):
    template_path = "template/basic_scenario.tpl"
    expected_status_code = kwargs.get("expected_status_code")
    if expected_status_code == "1":
        template_path = "template/1_success_request_scenario.tpl"
    elif expected_status_code == "2":
        template_path = "template/2_not_found_by_delete.tpl"
    elif expected_status_code == "3":
        template_path = "template/3_not_found_by_invalid_parameters.tpl"

    with open(template_path, "r") as file:
        template = file.read()
    endpoint = kwargs.get("endpoint")
    relevant_endpoints = kwargs.get("relevant_endpoints")
    delete_operation = kwargs.get("delete_operation")
    scenario = template.format_map(
        SafeDict(
            endpoint=endpoint,
            expected_status_code=expected_status_code,
            relevant_endpoints=relevant_endpoints,
            delete_operation=delete_operation,
        )
    )
    
    return scenario


def generate_scenario(**kwargs):
    with open("template/scenario_prompt.tpl", "r") as file:
        template = file.read()
    expected_status_code = kwargs.get("expected_status_code")
    endpoint = kwargs.get("endpoint")
    expected_status_code = kwargs.get("expected_status_code")
    relevant_endpoints = kwargs.get("relevant_endpoints")

    prompt = template.format_map(
        SafeDict(
            endpoint=endpoint,
            expected_status_code=expected_status_code,
            relevant_endpoints=",".join(relevant_endpoints),
        )
    )
    system_prompt = "You are an expert in testing for restful apis, you need to generate a test scenario for a given endpoint."
    
    return GPTChatCompletion(prompt, system_prompt)