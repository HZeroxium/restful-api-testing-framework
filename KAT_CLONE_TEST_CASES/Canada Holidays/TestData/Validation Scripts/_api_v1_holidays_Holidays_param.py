```python
def validate_request_data(request_data_item):
    try:
        if "year" not in request_data_item:
            return False
        if "federal" in request_data_item and request_data_item["federal"] not in ["true", "false", "1", "0"]:
            return False
    except:
        pass

    try:
        if "optional" in request_data_item and request_data_item["optional"] not in ["true", "false", "1", "0"]:
            return False
    except:
        pass

    return True
```

print(validate_request_data({request_data_item}))