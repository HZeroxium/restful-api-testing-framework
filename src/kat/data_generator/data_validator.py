

class DataValidator:
    @staticmethod
    def is_valid_response_schema(schema, response):
        for key, value in schema.items():
            if key not in response:
                return False
            if isinstance(value, dict):
                if not DataValidator.is_valid_response(value, response[key]):
                    return False
            elif isinstance(value, list):
                if not isinstance(response[key], list):
                    return False
                for item in response[key]:
                    if not DataValidator.is_valid_response(value[0], item):
                        return False   
        return True