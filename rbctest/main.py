import json

from oas_parser.operations import OperationProcessor


def main():
    with open(
        "/media/aaronpham5504/New Volume/Research/restful-api-testing-framework/rbctest/example/Canada Holidays/openapi.json",
        "r",
    ) as file:
        data = json.load(file)
    operation_processor = OperationProcessor(data)
    simplify_content = operation_processor.simplify_openapi()

    with open("simplify.json", "w") as file:
        json.dump(simplify_content, file, indent=2)


if __name__ == "__main__":
    main()
