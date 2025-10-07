import re

from kat.document_parser.document_parser import extract_endpoints_simplified_swagger_spec
class SafeDict(dict):
    def __missing__(self, key):
        return ""

def standardize_test_script(test_script_core, endpoint_index):
    if test_script_core is None or test_script_core == "":
        return test_script_core
    
    test_script_core = test_script_core.replace("path_variable_declaration", f"path_variables_{endpoint_index}")
    test_script_core = test_script_core.replace("query_parameter_declaration", f"query_parameters_{endpoint_index}")
    test_script_core = test_script_core.replace("request_body_declaration", f"request_body_{endpoint_index}")
    test_script_core = test_script_core.replace("body_var", f"body_{endpoint_index}")
    test_script_core = test_script_core.replace("param_var", f"param_{endpoint_index}")
    test_script_core = test_script_core.replace("latest_body", f"body_{endpoint_index}")

    return test_script_core


def extract_test_script_core(gpt_response):
    patterns = [
        r"```code\n(?P<code>.*?)\n```",
        r"```\n(?P<code>.*?)\n```"
    ]
    
    for pattern in patterns:
        x = re.search(pattern, gpt_response, re.DOTALL)
        if x:
            return x.group("code")
    
    return None
def generate_prompt(
    basic_prompt_template,
    endpoints_spec,
    endpoint,
    sequence
):

    with open(basic_prompt_template, "r") as file:
        template = file.read()
    
    endpoints_definition = extract_endpoints_simplified_swagger_spec(endpoints_spec, sequence)

    # ### Generate parameters description ###
    # with open("KataApiTestGen/template/parameters_description.tpl", "r") as file:
    #     params_description_template = file.read()
        
    # params_description_prompt = params_description_template.format_map(
    #     SafeDict(
    #         endpoints_definition=endpoints_definition,
    #     )
    # )

    prompt = template.format_map(
        SafeDict(
            endpoint=endpoint,
            relevant_endpoints=', '.join(sequence[:-1]),
            endpoints_definition=endpoints_definition,
            # parameter_description = GPTChatCompletion(params_description_prompt),
            parameter_description = ""
        )
    )

    return prompt