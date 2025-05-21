def find_object_with_key(json_obj, target_key):
    if isinstance(json_obj, dict):
        if target_key in json_obj:
            return json_obj
        for value in json_obj.values():
            result = find_object_with_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_object_with_key(item, target_key)
            if result is not None:
                return result
    return None


def extract_ref_values(json_obj):
    refs = []

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key == "$ref":
                refs.append(value)
            else:
                refs.extend(
                    extract_ref_values(value)
                )  # Recursively search nested values
    elif isinstance(json_obj, list):
        for item in json_obj:
            refs.extend(extract_ref_values(item))  # Recursively search items in a list

    return list(set(refs))
