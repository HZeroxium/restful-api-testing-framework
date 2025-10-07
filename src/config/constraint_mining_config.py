# config/constraint_mining_config.py

"""Configuration constants for constraint mining operations."""

from enum import Enum
from typing import Dict, List


class ConstraintSeverity(str, Enum):
    """Severity levels for constraints."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ConstraintCategory(str, Enum):
    """Categories of constraints."""

    REQUIRED = "required"
    TYPE = "type"
    FORMAT = "format"
    RANGE = "range"
    ENUM = "enum"
    PATTERN = "pattern"
    STRUCTURE = "structure"
    LIMIT = "limit"
    CONSISTENCY = "consistency"
    CORRELATION = "correlation"


class ResponseAnalysisConfig:
    """Configuration for response property constraint analysis."""

    # Chunking thresholds
    DEFAULT_CHUNK_THRESHOLD: int = 20
    DEFAULT_MAX_CHUNK_SIZE: int = 15
    MIN_COMPLEXITY_ESTIMATE: int = 5

    # Processing limits
    MAX_RETRIES: int = 3
    CHUNK_OVERLAP: int = 2


class ParameterAnalysisConfig:
    """Configuration for parameter constraint analysis."""

    # Parameter locations
    PARAMETER_LOCATIONS: List[str] = ["query", "path", "header", "cookie"]

    # Common parameter patterns
    SECURITY_PARAMETERS: List[str] = [
        "api_key",
        "authorization",
        "token",
        "session_id",
        "auth_token",
    ]

    # Standard parameter types
    PARAMETER_TYPES: List[str] = [
        "string",
        "integer",
        "boolean",
        "number",
        "array",
        "object",
    ]


class RequestBodyAnalysisConfig:
    """Configuration for request body constraint analysis."""

    # HTTP methods that typically use request bodies
    BODY_METHODS: List[str] = ["POST", "PUT", "PATCH"]

    # HTTP methods that typically don't use request bodies
    NO_BODY_METHODS: List[str] = ["GET", "DELETE", "HEAD", "OPTIONS"]

    # Common content types
    SUPPORTED_CONTENT_TYPES: List[str] = [
        "application/json",
        "application/xml",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
    ]


class CorrelationAnalysisConfig:
    """Configuration for request-response correlation analysis."""

    # Common correlation types
    CORRELATION_TYPES: List[str] = [
        "filter",
        "pagination",
        "sort",
        "reflection",
        "conditional",
        "validation",
        "state_change",
        "authentication",
    ]

    # Common request elements that affect responses
    FILTER_PARAMETERS: List[str] = [
        "filter",
        "search",
        "query",
        "q",
        "where",
        "include",
        "exclude",
    ]

    PAGINATION_PARAMETERS: List[str] = [
        "page",
        "offset",
        "limit",
        "size",
        "per_page",
        "page_size",
    ]

    SORT_PARAMETERS: List[str] = ["sort", "order", "order_by", "sort_by", "direction"]


class LLMPromptConfig:
    """Configuration for LLM prompt templates."""

    # Common instruction prefixes
    CRITICAL_INSTRUCTION_PREFIX = """**CRITICAL INSTRUCTION: Use ONLY information present in the provided endpoint_data. Do NOT invent, assume, or add any constraints that are not explicitly defined in the OpenAPI specification. Extract constraints solely based on the OpenAPI specification data provided.**"""

    # Template formatting
    PATH_PARAMETER_NOTE = """Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces to avoid template conflicts."""

    # Response format instructions
    JSON_FORMAT_INSTRUCTION = """Return your analysis in the specified JSON format with a "constraints" array."""

    # Fallback messages
    FALLBACK_REASON_NO_BODY = "Method doesn't typically use request body"
    FALLBACK_REASON_LLM_ERROR = "LLM analysis failed, using fallback constraints"
    FALLBACK_SOURCE = "fallback"

    # Status indicators
    STATUS_SUCCESS = "success"
    STATUS_SKIPPED = "skipped"
    STATUS_SUCCESS_FALLBACK = "success_fallback"
    STATUS_ERROR = "error"


class CacheConfig:
    """Configuration for caching in constraint mining."""

    # Cache keys
    CACHE_KEY_PREFIX = "constraint_mining"
    PARAM_CACHE_KEY = f"{CACHE_KEY_PREFIX}_param"
    BODY_CACHE_KEY = f"{CACHE_KEY_PREFIX}_body"
    RESPONSE_CACHE_KEY = f"{CACHE_KEY_PREFIX}_response"
    CORRELATION_CACHE_KEY = f"{CACHE_KEY_PREFIX}_correlation"

    # Cache TTL (in seconds)
    DEFAULT_CACHE_TTL = 3600  # 1 hour

    # Cache size limits
    MAX_CACHE_SIZE = 1000
