```python
def validate_request_data(request_data_item):
    try:
        if "publicationId" in request_data_item and "documentId" in request_data_item:
            return True
        else:
            return False
    except:
        pass

    try:
        if "documentId" in request_data_item and "publicationId" in request_data_item:
            return True
        else:
            return False
    except:
        pass

    return True
```

print(validate_request_data({request_data_item}))