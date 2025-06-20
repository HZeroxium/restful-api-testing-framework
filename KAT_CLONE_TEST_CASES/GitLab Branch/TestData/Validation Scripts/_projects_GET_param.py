```python
def validate_request_data(request_data_item):
    try:
        if "id_after" in request_data_item and "id_before" in request_data_item:
            if request_data_item["id_after"] <= request_data_item["id_before"]:
                return False
    except:
        pass

    try:
        if "last_activity_after" in request_data_item and "last_activity_before" in request_data_item:
            if request_data_item["last_activity_after"] >= request_data_item["last_activity_before"]:
                return False
    except:
        pass

    try:
        if "order_by" in request_data_item and "sort" in request_data_item:
            if request_data_item["order_by"] and request_data_item["sort"]:
                return True
    except:
        pass

    try:
        if "repository_storage" in request_data_item and "with_custom_attributes" in request_data_item:
            if request_data_item["repository_storage"] and request_data_item["with_custom_attributes"]:
                return True
    except:
        pass

    try:
        if "with_custom_attributes" in request_data_item and "with_issues_enabled" in request_data_item:
            if request_data_item["with_custom_attributes"] and request_data_item["with_issues_enabled"]:
                return True
    except:
        pass

    try:
        if "with_custom_attributes" in request_data_item and "with_merge_requests_enabled" in request_data_item:
            if request_data_item["with_custom_attributes"] and request_data_item["with_merge_requests_enabled"]:
                return True
    except:
        pass

    return True
```

print(validate_request_data({request_data_item}))