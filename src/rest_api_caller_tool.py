# src/rest_api_caller_tool.py

import asyncio
import os
import json
from datetime import datetime

from tools.core.rest_api_caller import RestApiCallerTool
from schemas.tools.rest_api_caller import RestApiCallerInput, RestRequest
from common.logger import LoggerFactory, LoggerType, LogLevel


async def main():
    # Initialize logger for the demo
    logger = LoggerFactory.get_logger(
        name="rest-api-caller-demo",
        logger_type=LoggerType.STANDARD,
        level=LogLevel.INFO,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "rest_api_caller", ts)
    os.makedirs(out_dir, exist_ok=True)

    logger.info("Starting REST API Caller Tool demo")
    logger.add_context(output_directory=out_dir, timestamp=ts)

    tool = RestApiCallerTool(verbose=True, cache_enabled=False, config={"timeout": 5})

    examples = {
        # Simple GET
        "httpbin_get": RestRequest(
            method="GET", url="https://httpbin.org/get", params={"show_env": 1}
        ),
        # JSON POST
        "httpbin_post": RestRequest(
            method="POST", url="https://httpbin.org/post", json={"foo": "bar"}
        ),
        # JSONPlaceholder examples
        "get_posts": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts",
        ),
        "get_post_1": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts/1",
        ),
        "create_post": RestRequest(
            method="POST",
            url="https://jsonplaceholder.typicode.com/posts",
            headers={"Content-type": "application/json; charset=UTF-8"},
            json={"title": "foo", "body": "bar", "userId": 1},
        ),
        "update_post_1": RestRequest(
            method="PUT",
            url="https://jsonplaceholder.typicode.com/posts/1",
            headers={"Content-type": "application/json; charset=UTF-8"},
            json={"id": 1, "title": "foo", "body": "bar", "userId": 1},
        ),
        "patch_post_1": RestRequest(
            method="PATCH",
            url="https://jsonplaceholder.typicode.com/posts/1",
            headers={"Content-type": "application/json; charset=UTF-8"},
            json={"title": "updated title"},
        ),
        "delete_post_1": RestRequest(
            method="DELETE",
            url="https://jsonplaceholder.typicode.com/posts/1",
        ),
        "filter_posts_user_1": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts",
            params={"userId": 1},
        ),
        "get_post_comments": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/posts/1/comments",
        ),
        "list_comments": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/comments",
        ),
        "filter_comments_post_1": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/comments",
            params={"postId": 1},
        ),
        "list_albums": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/albums",
        ),
        "get_album_photos": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/albums/1/photos",
        ),
        "get_user_albums": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1/albums",
        ),
        "get_user_todos": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1/todos",
        ),
        "get_user_posts": RestRequest(
            method="GET",
            url="https://jsonplaceholder.typicode.com/users/1/posts",
        ),
    }

    logger.info(f"Running {len(examples)} REST API examples")

    for name, req in examples.items():
        logger.info(f"Executing example: {name}")
        logger.add_context(
            example_name=name,
            method=req.method,
            url=req.url,
            has_params=bool(req.params),
            has_json=bool(req.json),
        )

        try:
            inp = RestApiCallerInput(request=req)
            result = await tool.execute(inp)

            path = os.path.join(out_dir, f"{name}.json")
            with open(path, "w") as f:
                json.dump(result.model_dump(), f, indent=2)

            logger.info(f"Example '{name}' completed successfully")
            logger.add_context(
                status_code=result.response.status_code,
                response_time=f"{result.elapsed:.3f}s",
                output_file=path,
            )
            logger.debug(f"Response saved to: {path}")

        except Exception as e:
            logger.error(f"Error executing example '{name}': {str(e)}")
            logger.add_context(error=str(e))

    logger.info("REST API Caller Tool demo completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
