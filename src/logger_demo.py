# src/logger_demo.py
"""
Comprehensive demonstration of the extensible logging system
"""

import time
from pathlib import Path

from common.logger import (
    LogLevel,
    StandardLogger,
    PrintLogger,
    LoggerFactory,
    LoggerType,
)


def demo_basic_logging():
    """Demonstrate basic logging functionality"""
    print("=" * 80)
    print("🎯 DEMO 1: Basic Logging Functionality")
    print("=" * 80)

    # Create standard logger
    logger = StandardLogger(name="demo-basic", level=LogLevel.DEBUG)

    print("\n📝 Testing all log levels:")
    logger.debug("This is a debug message - useful for development")
    logger.info("This is an info message - general information")
    logger.warning("This is a warning message - something to be aware of")
    logger.error("This is an error message - something went wrong")
    logger.critical("This is a critical message - urgent attention needed")

    print("\n📝 Testing with format arguments:")
    logger.info("User %s logged in from %s", "john_doe", "192.168.1.100")
    logger.error(
        "Failed to connect to %s:%d after %d attempts", "api.example.com", 443, 3
    )


def demo_context_logging():
    """Demonstrate contextual logging"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 2: Contextual Logging")
    print("=" * 80)

    logger = StandardLogger(name="demo-context", level=LogLevel.DEBUG)

    print("\n📝 Adding context information:")
    logger.add_context(user_id="12345", session_id="abc-def-ghi", request_id="req-001")

    logger.info("Processing API request")
    logger.debug("Validating request parameters")
    logger.warning("Rate limit approaching threshold")

    print("\n📝 Updating context:")
    logger.add_context(endpoint="/api/v1/users", method="GET")
    logger.info("Request processed successfully")

    print("\n📝 Clearing context:")
    logger.clear_context()
    logger.info("Context cleared - no more contextual info")


def demo_different_loggers():
    """Demonstrate different logger implementations"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 3: Different Logger Implementations")
    print("=" * 80)

    print("\n📝 Standard Logger (with colors):")
    standard_logger = StandardLogger(name="standard-colored", use_colors=True)
    standard_logger.info("Beautiful colored output! 🌈")
    standard_logger.warning("Warning with colors!")
    standard_logger.error("Error with colors!")

    print("\n📝 Standard Logger (without colors):")
    standard_plain = StandardLogger(name="standard-plain", use_colors=False)
    standard_plain.info("Plain output without colors")
    standard_plain.warning("Plain warning message")

    print("\n📝 Print Logger:")
    print_logger = PrintLogger(name="print-logger")
    print_logger.info("Simple print-based logging")
    print_logger.warning("Print logger warning")
    print_logger.error("Print logger error")


def demo_log_levels():
    """Demonstrate log level filtering"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 4: Log Level Filtering")
    print("=" * 80)

    logger = StandardLogger(name="demo-levels")

    print("\n📝 Setting log level to WARNING (should filter out DEBUG and INFO):")
    logger.set_level(LogLevel.WARNING)

    logger.debug("This debug message should be filtered out")
    logger.info("This info message should be filtered out")
    logger.warning("This warning message should appear")
    logger.error("This error message should appear")
    logger.critical("This critical message should appear")

    print("\n📝 Setting log level back to DEBUG (should show all messages):")
    logger.set_level(LogLevel.DEBUG)

    logger.debug("Now debug messages appear again")
    logger.info("And info messages too")


def demo_factory_pattern():
    """Demonstrate logger factory usage"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 5: Logger Factory Pattern")
    print("=" * 80)

    print("\n📝 Getting cached logger instances:")

    # Get same logger instance (cached)
    logger1 = LoggerFactory.get_logger("api-service", LoggerType.STANDARD)
    logger2 = LoggerFactory.get_logger("api-service", LoggerType.STANDARD)

    print(f"Logger instances are same: {logger1 is logger2}")

    logger1.add_context(component="auth")
    logger1.info("Message from logger1")

    # logger2 should have the same context since it's the same instance
    logger2.info("Message from logger2 (same instance)")

    print("\n📝 Creating different logger types:")

    standard_logger = LoggerFactory.get_logger("service-a", LoggerType.STANDARD)
    print_logger = LoggerFactory.get_logger("service-b", LoggerType.PRINT)

    standard_logger.info("Message from standard logger")
    print_logger.info("Message from print logger")

    print("\n📝 Creating new instances (not cached):")
    new_logger1 = LoggerFactory.create_logger("temp-service", LoggerType.STANDARD)
    new_logger2 = LoggerFactory.create_logger("temp-service", LoggerType.STANDARD)

    print(f"New logger instances are different: {new_logger1 is not new_logger2}")


def demo_file_logging():
    """Demonstrate file logging"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 6: File Logging")
    print("=" * 80)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "demo.log"

    print(f"\n📝 Logging to file: {log_file}")

    # Create logger with file output
    logger = StandardLogger(
        name="file-logger", level=LogLevel.DEBUG, log_file=str(log_file)
    )

    logger.add_context(demo="file-logging", timestamp=time.time())

    logger.info("This message goes to both console and file")
    logger.warning("Warning message with context")
    logger.error("Error message for file logging demo")

    print(f"\n📄 Log file created: {log_file.exists()}")
    if log_file.exists():
        print(f"📄 Log file size: {log_file.stat().st_size} bytes")


def demo_api_testing_scenario():
    """Demonstrate realistic API testing scenario"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 7: Realistic API Testing Scenario")
    print("=" * 80)

    # Create logger for API testing framework
    logger = LoggerFactory.get_logger(
        name="api-testing-framework",
        logger_type=LoggerType.STANDARD,
        level=LogLevel.DEBUG,
    )

    print("\n📝 Simulating API test execution:")

    # Test suite start
    logger.add_context(test_suite="user_management", version="v1.2.3")
    logger.info("🚀 Starting API test suite execution")

    # Individual test case
    logger.add_context(
        test_case="test_create_user", method="POST", endpoint="/api/v1/users"
    )
    logger.debug("Preparing test data")
    logger.info("Executing API call")

    # Simulate success
    logger.add_context(status_code=201, response_time="245ms")
    logger.info("✅ Test passed - User created successfully")

    # Another test case
    logger.clear_context()
    logger.add_context(
        test_suite="user_management",
        test_case="test_invalid_email",
        method="POST",
        endpoint="/api/v1/users",
    )

    logger.debug("Testing with invalid email format")
    logger.info("Executing API call with invalid data")

    # Simulate validation error
    logger.add_context(status_code=400, error_code="INVALID_EMAIL")
    logger.info("✅ Test passed - Validation error caught as expected")

    # Simulate test failure
    logger.clear_context()
    logger.add_context(
        test_suite="user_management",
        test_case="test_user_permissions",
        method="GET",
        endpoint="/api/v1/users/12345",
    )

    logger.error("❌ Test failed - Unexpected 500 status code")
    logger.add_context(status_code=500, error="Internal Server Error")
    logger.critical("🚨 Critical: Database connection failed")

    # Test suite summary
    logger.clear_context()
    logger.add_context(total_tests=15, passed=13, failed=2, execution_time="2.3s")
    logger.info("📊 Test suite execution completed")


def demo_performance_comparison():
    """Compare performance of different logger implementations"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 8: Performance Comparison")
    print("=" * 80)

    import time

    # Test message count
    message_count = 1000

    print(f"\n📝 Performance test with {message_count} messages:")

    # Test StandardLogger
    standard_logger = StandardLogger(name="perf-standard", level=LogLevel.INFO)

    start_time = time.time()
    for i in range(message_count):
        standard_logger.info(f"Performance test message {i}")
    standard_time = time.time() - start_time

    # Test PrintLogger
    print_logger = PrintLogger(name="perf-print", level=LogLevel.INFO)

    start_time = time.time()
    for i in range(message_count):
        print_logger.info(f"Performance test message {i}")
    print_time = time.time() - start_time

    print(f"\n📊 Performance Results:")
    print(f"   StandardLogger: {standard_time:.3f} seconds")
    print(f"   PrintLogger: {print_time:.3f} seconds")
    print(f"   Difference: {abs(standard_time - print_time):.3f} seconds")


def demo_separate_console_file_levels():
    """Demonstrate separate console and file log levels"""
    print("\n" + "=" * 80)
    print("🎯 DEMO 9: Separate Console and File Log Levels")
    print("=" * 80)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "console_file_demo.log"

    print(f"\n📝 Creating logger with separate levels:")
    print("   - Console: INFO and above")
    print("   - File: DEBUG and above")
    print(f"   - Log file: {log_file}")

    # Create logger with separate console and file levels
    logger = StandardLogger(
        name="console-file-demo",
        console_level=LogLevel.INFO,  # Only INFO+ to console
        file_level=LogLevel.DEBUG,  # DEBUG+ to file
        log_file=str(log_file),
        use_colors=True,
    )

    logger.add_context(demo="separate-levels", test_case="llm_logging")

    print("\n📝 Testing log levels (check console vs file):")
    logger.debug("This DEBUG message should appear ONLY in file")
    logger.info("This INFO message should appear in BOTH console and file")
    logger.warning("This WARNING message should appear in BOTH console and file")
    logger.error("This ERROR message should appear in BOTH console and file")

    print(f"\n📄 Check the log file {log_file} to see DEBUG messages")

    # Demonstrate dynamic level changes
    print("\n📝 Changing console level to DEBUG:")
    logger.set_console_level(LogLevel.DEBUG)
    logger.debug("Now this DEBUG message appears in BOTH console and file")

    print("\n📝 Changing file level to WARNING:")
    logger.set_file_level(LogLevel.WARNING)
    logger.debug("This DEBUG message appears ONLY on console now")
    logger.info("This INFO message appears ONLY on console now")
    logger.warning("This WARNING message appears in BOTH console and file")

    print(f"\n📊 Current levels:")
    print(f"   - Console level: {logger.get_console_level().value}")
    print(
        f"   - File level: {logger.get_file_level().value if logger.get_file_level() else 'None'}"
    )


def main():
    """Run all logging demos"""
    print("🎉 Welcome to the Extensible Logging System Demo!")
    print("This demo showcases the capabilities of our logging framework.")

    # Run all demos
    demo_basic_logging()
    demo_context_logging()
    demo_different_loggers()
    demo_log_levels()
    demo_factory_pattern()
    demo_file_logging()
    demo_api_testing_scenario()
    demo_performance_comparison()
    demo_separate_console_file_levels()  # New demo

    print("\n" + "=" * 80)
    print("🎊 Demo completed! The logging system is ready for use.")
    print("=" * 80)

    print("\n💡 Quick Usage Examples:")
    print("   # Get a standard logger")
    print("   from common.logger import LoggerFactory, LoggerType")
    print("   logger = LoggerFactory.get_logger('my-service', LoggerType.STANDARD)")
    print("   ")
    print("   # Log with context")
    print("   logger.add_context(user_id='123', action='login')")
    print("   logger.info('User authentication successful')")
    print("   ")
    print("   # Use different log levels")
    print("   logger.debug('Debug info')")
    print("   logger.warning('Something to note')")
    print("   logger.error('An error occurred')")


if __name__ == "__main__":
    main()
