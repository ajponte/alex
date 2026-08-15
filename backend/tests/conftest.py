"""
Pytest configuration and global fixtures for Alex backend tests.
Ensures test collection and execution proceed deterministically without requiring live AWS Aurora credentials.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Default environment variables for testing when AWS Aurora / Clerk / SQS credentials are absent
DEFAULT_TEST_ENV = {
    "AURORA_CLUSTER_ARN": "arn:aws:rds:us-east-1:123456789012:cluster:dummy-test-cluster",
    "AURORA_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:dummy-test-secret",
    "AURORA_DATABASE": "alex_test",
    "DEFAULT_AWS_REGION": "us-east-1",
    "AWS_DEFAULT_REGION": "us-east-1",
    "CLERK_JWKS_URL": "https://example.clerk.accounts.dev/.well-known/jwks.json",
    "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
}


def _apply_default_env():
    for key, val in DEFAULT_TEST_ENV.items():
        if not os.environ.get(key):
            os.environ[key] = val


# Apply defaults immediately upon conftest module import
_apply_default_env()


def pytest_configure(config):
    """Ensure environment defaults are set before test collection phase."""
    _apply_default_env()
