# src/rest_api_caller_tool.py

import asyncio
import os
import json
from datetime import datetime

from tools.rest_api_caller import RESTAPICallerTool
from schemas.tools.rest_api_caller import RESTAPICallerInput, RESTRequest


async def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "rest_api_caller", ts)
    os.makedirs(out_dir, exist_ok=True)

    tool = RESTAPICallerTool(verbose=True, cache_enabled=False, config={"timeout": 5})

    examples = {
        # Simple GET
        "httpbin_get": RESTRequest(
            method="GET", url="https://httpbin.org/get", params={"show_env": 1}
        ),
        # JSON POST
        "httpbin_post": RESTRequest(
            method="POST", url="https://httpbin.org/post", json={"foo": "bar"}
        ),
        # JSONPlaceholder examples
        "get_posts": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts",
        ),
        "get_post_1": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts/1",
        ),
        "create_post": RESTRequest(
            method="POST",
            url="https://jsonplaceholder.typicode.com/posts",
            headers={"Content-type": "application/json; charset=UTF-8"},
            json={"title": "foo", "body": "bar", "userId": 1},
        ),
        "update_post_1": RESTRequest(
            method="PUT",
            url="https://jsonplaceholder.typicode.com/posts/1",
            headers={"Content-type": "application/json; charset=UTF-8"},
            json={"id": 1, "title": "foo", "body": "bar", "userId": 1},
        ),
        "patch_post_1": RESTRequest(
            method="PATCH",
            url="https://jsonplaceholder.typicode.com/posts/1",
            headers={"Content-type": "application/json; charset=UTF-8"},
            json={"title": "updated title"},
        ),
        "delete_post_1": RESTRequest(
            method="DELETE",
            url="https://jsonplaceholder.typicode.com/posts/1",
        ),
        "filter_posts_user_1": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts",
            params={"userId": 1},
        ),
        "get_post_comments": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts/1/comments",
        ),
        "list_comments": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/comments",
        ),
        "filter_comments_post_1": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/comments",
            params={"postId": 1},
        ),
        "list_albums": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/albums",
        ),
        "get_album_photos": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/albums/1/photos",
        ),
        "get_user_albums": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1/albums",
        ),
        "get_user_todos": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1/todos",
        ),
        "get_user_posts": RESTRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1/posts",
        ),
    }

    for name, req in examples.items():
        print(f"\n--- Example: {name} ---")
        inp = RESTAPICallerInput(request=req)
        result = await tool.execute(inp)

        path = os.path.join(out_dir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        print(f"Wrote {path}")


if __name__ == "__main__":
    asyncio.run(main())
