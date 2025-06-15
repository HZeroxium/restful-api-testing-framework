```python
def validate_request_data(request_data_item):
    try:
        if "year" in request_data_item:
            year = request_data_item["year"]
            if not isinstance(year, int):
                return False
    except:
        pass

    try:
        if "optional" in request_data_item:
            optional = request_data_item["optional"]
            if not isinstance(optional, str):
                return False
            if optional.lower() not in ["false", "0", "true", "1"]:
                return False
    except:
        pass

    return True
```

print(validate_request_data({request_data_item}))