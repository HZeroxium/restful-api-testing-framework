```python
def validate_request_data(request_data_item):
    try:
        # Check dependency 1
        if "holidayId" not in request_data_item or not isinstance(request_data_item["holidayId"], int):
            return False
        if "year" not in request_data_item or not isinstance(request_data_item["year"], int):
            return False
    except:
        pass  # Skip this dependency if an error occurs

    try:
        # Check dependency 2
        if "holidayId" not in request_data_item or not isinstance(request_data_item["holidayId"], int):
            return False
        if "optional" not in request_data_item or not isinstance(request_data_item["optional"], str):
            return False
    except:
        pass  # Skip this dependency if an error occurs

    return True
```

print(validate_request_data({request_data_item}))