```python
def validate_request_data(request_data_item):
    try:
        if request_data_item["provinceId"] in ["AB", "BC"]:
            if request_data_item["provinceId"] == "AB" or request_data_item["provinceId"] == "BC":
                if "optional" not in request_data_item:
                    return False
                elif request_data_item["optional"] not in ["true", "false", "1", "0"]:
                    return False
    except:
        pass

    return True
```

print(validate_request_data({request_data_item}))