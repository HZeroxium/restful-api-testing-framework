```python
def validate_request_data(request_data_item):
    try:
        if "billId" not in request_data_item:
            return False
    except:
        pass

    try:
        if "billStageId" not in request_data_item:
            return False
    except:
        pass

    return True
```

print(validate_request_data({request_data_item}))