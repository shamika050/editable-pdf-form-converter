#!/usr/bin/env python3
"""
Configuration Management Module

Loads configuration from environment variables or .env file.
Validates required API credentials are present.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Looks for .env file in project root and loads variables if found.

    Returns:
        Dictionary with configuration sections:
        - aws: AWS Textract credentials
        - anthropic: Claude API credentials
        - processing: Processing parameters
    """
    # Try to load from .env file if it exists
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists():
        _load_env_file(env_file)

    return {
        'aws': {
            'access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        },
        'anthropic': {
            'api_key': os.getenv('ANTHROPIC_API_KEY')
        },
        'processing': {
            'max_workers': int(os.getenv('MAX_WORKERS', '4')),
            'dpi': int(os.getenv('DEFAULT_DPI', '200')),
            'confidence_threshold': int(os.getenv('CONFIDENCE_THRESHOLD', '70'))
        }
    }


def _load_env_file(env_file: Path) -> None:
    """
    Load environment variables from .env file.

    Args:
        env_file: Path to .env file
    """
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=value format
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


def validate_config(config: Dict[str, Any], require_anthropic: bool = True) -> bool:
    """
    Validate that required configuration values are present.

    Args:
        config: Configuration dictionary from load_config()
        require_anthropic: Whether to require Anthropic API key (default True)

    Returns:
        True if valid

    Raises:
        EnvironmentError: If required configuration is missing
    """
    errors = []

    # Check AWS credentials
    if not config['aws']['access_key_id']:
        errors.append("AWS_ACCESS_KEY_ID not set")
    if not config['aws']['secret_access_key']:
        errors.append("AWS_SECRET_ACCESS_KEY not set")

    # Check Anthropic API key if required
    if require_anthropic and not config['anthropic']['api_key']:
        errors.append("ANTHROPIC_API_KEY not set")

    if errors:
        error_msg = f"Configuration errors:\n  - " + "\n  - ".join(errors)
        error_msg += "\n\nPlease copy .env.example to .env and fill in your API credentials."
        raise EnvironmentError(error_msg)

    return True


def get_aws_credentials(config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Get AWS credentials dictionary suitable for boto3.

    Args:
        config: Optional config dict. If None, will call load_config()

    Returns:
        Dictionary with aws_access_key_id, aws_secret_access_key, region_name
    """
    if config is None:
        config = load_config()

    return {
        'aws_access_key_id': config['aws']['access_key_id'],
        'aws_secret_access_key': config['aws']['secret_access_key'],
        'region_name': config['aws']['region']
    }


def get_anthropic_api_key(config: Optional[Dict[str, Any]] = None) -> str:
    """
    Get Anthropic API key.

    Args:
        config: Optional config dict. If None, will call load_config()

    Returns:
        Anthropic API key string

    Raises:
        EnvironmentError: If API key not set
    """
    if config is None:
        config = load_config()

    api_key = config['anthropic']['api_key']
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. "
            "Please copy .env.example to .env and add your API key."
        )

    return api_key

def _mask_value(value: Optional[str]) -> str:
    """Mask sensitive values for display."""
    if not value:
        return "<NOT SET>"
    if len(value) <= 8:
        return "***"
    return value[:4] + "..." + value[-4:]

# Example usage
if __name__ == "__main__":
    print("PDF Form Converter - Configuration Check\n")
    print("=" * 60)

    try:
        config = load_config()

        print("\n✓ Configuration loaded successfully\n")

        # Show configuration (masked)
        print("AWS Configuration:")
        print(f"  Access Key ID: {_mask_value(config['aws']['access_key_id'])}")
        print(f"  Secret Key: {_mask_value(config['aws']['secret_access_key'])}")
        print(f"  Region: {config['aws']['region']}")

        print("\nAnthropic Configuration:")
        print(f"  API Key: {_mask_value(config['anthropic']['api_key'])}")

        print("\nProcessing Configuration:")
        print(f"  Max Workers: {config['processing']['max_workers']}")
        print(f"  Default DPI: {config['processing']['dpi']}")
        print(f"  Confidence Threshold: {config['processing']['confidence_threshold']}%")

        # Validate
        print("\n" + "=" * 60)
        print("Validating configuration...")
        validate_config(config)
        print("✓ All required credentials are set\n")

    except EnvironmentError as e:
        print(f"\n✗ Configuration Error:\n{e}\n")
        exit(1)
