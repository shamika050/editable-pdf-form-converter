#!/usr/bin/env python3
"""
AWS Textract Diagnostic Script
Checks if your AWS credentials have Textract access.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "pdf-form-converter/scripts"))

import boto3
from botocore.exceptions import ClientError
from config import load_config, get_aws_credentials

print("AWS Textract Access Diagnostic")
print("=" * 60)

# Load config
try:
    config = load_config()
    aws_creds = get_aws_credentials(config)
    print("\n✓ Configuration loaded successfully")
    print(f"  Region: {aws_creds['region_name']}")
    print(f"  Access Key: {aws_creds['aws_access_key_id'][:8]}...")
except Exception as e:
    print(f"\n✗ Configuration Error: {e}")
    sys.exit(1)

# Test AWS connection
print("\n" + "-" * 60)
print("Testing AWS Connection...")
print("-" * 60)

try:
    # Create Textract client
    textract = boto3.client('textract', **aws_creds)
    print("✓ Textract client created")

    # Try to list Textract service quotas (doesn't require subscription)
    sts = boto3.client('sts', **aws_creds)
    identity = sts.get_caller_identity()
    print(f"✓ AWS Account ID: {identity['Account']}")
    print(f"✓ User ARN: {identity['Arn']}")

except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"\n✗ AWS Error: {error_code}")
    print(f"  Message: {e.response['Error']['Message']}")

    if error_code == 'InvalidClientTokenId':
        print("\n  → Your AWS Access Key ID is invalid")
        print("  → Generate new credentials in AWS IAM Console")
    elif error_code == 'SignatureDoesNotMatch':
        print("\n  → Your AWS Secret Access Key is incorrect")
        print("  → Check for typos in .env file")
    else:
        print(f"\n  → Unknown error: {error_code}")

    sys.exit(1)

# Test Textract access
print("\n" + "-" * 60)
print("Testing Textract Access...")
print("-" * 60)

try:
    # Try to call Textract with minimal data
    # This will fail with SubscriptionRequiredException if not enabled
    response = textract.detect_document_text(
        Document={'Bytes': b'%PDF-1.4\n'}  # Minimal PDF header
    )
    print("✓ Textract access confirmed!")
    print("  Your account has Textract enabled")

except ClientError as e:
    error_code = e.response['Error']['Code']

    if error_code == 'SubscriptionRequiredException':
        print("✗ Textract Subscription Required")
        print("\n  Your AWS credentials are valid, but Textract is not enabled.")
        print("\n  To fix this:")
        print("  1. Go to: https://console.aws.amazon.com/textract/")
        print("  2. Click 'Get Started' or 'Enable Textract'")
        print("  3. Accept the terms of service")
        print("  4. Run this diagnostic again")

    elif error_code == 'AccessDeniedException':
        print("✗ Access Denied")
        print("\n  Your IAM user doesn't have Textract permissions.")
        print("\n  To fix this:")
        print("  1. Go to: https://console.aws.amazon.com/iam/")
        print("  2. Select your user")
        print("  3. Add policy: AmazonTextractFullAccess")

    elif error_code == 'InvalidParameterException':
        print("✓ Textract access confirmed!")
        print("  (Invalid test data, but service is accessible)")

    else:
        print(f"✗ Textract Error: {error_code}")
        print(f"  Message: {e.response['Error']['Message']}")

    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL CHECKS PASSED")
print("  Your AWS setup is ready for PDF form conversion!")
print("=" * 60)
