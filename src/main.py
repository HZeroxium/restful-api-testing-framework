# main.py

import uvicorn
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    logger.info("Starting RESTful API Testing Framework Server...")

    # Import app here to ensure proper module resolution
    from server import app
    from infra.configs.app_config import settings

    logger.info(f"Server will run on http://{settings.host}:{settings.port}")
    logger.info(
        f"API Documentation available at http://{settings.host}:{settings.port}/docs"
    )
    logger.info(f"ReDoc available at http://{settings.host}:{settings.port}/redoc")

    try:
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug",
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    # sequence_runner = SequenceRunner(service_name="Bill", base_url="https://bills-api.parliament.uk", token=None)
    sequence_runner = SequenceRunner(service_name="Canada Holidays", base_url="https://canada-holidays.ca", token=None)
    sequence_runner.run_all()