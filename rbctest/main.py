import json

from utils.openapi_utils import simplify_openapi


def main():
    with open(
        "/media/aaronpham5504/New Volume/Research/restful-api-testing-framework/rbctest/example/Canada Holidays/openapi.json",
        "r",
    ) as file:
        data = json.load(file)
    simplify_content = simplify_openapi(data)

    with open("simplify.json", "w") as file:
        json.dump(simplify_content, file, indent=2)


if __name__ == "__main__":
    main()
