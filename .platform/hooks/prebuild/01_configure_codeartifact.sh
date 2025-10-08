#!/bin/bash

# Configure AWS CodeArtifact for package installation during Elastic Beanstalk deployment
# This hook runs before the application dependencies are installed

set -e

echo "[CodeArtifact Hook] Starting CodeArtifact configuration..."

# CodeArtifact repository details
DOMAIN_NAME="proximal-code-artifact-domain"
ACCOUNT_ID="016997484973"
REGION="us-east-2"
REPOSITORY_NAME="proximal-hub"

# Get AWS CodeArtifact authorization token
echo "[CodeArtifact Hook] Getting authorization token..."
AWS_CODEARTIFACT_TOKEN=$(
    aws codeartifact get-authorization-token \
    --domain $DOMAIN_NAME \
    --domain-owner $ACCOUNT_ID \
    --region $REGION \
    --query authorizationToken \
    --output text
)

if [ -z "$AWS_CODEARTIFACT_TOKEN" ]; then
    echo "[CodeArtifact Hook] ERROR: Failed to get CodeArtifact token"
    exit 1
fi

echo "[CodeArtifact Hook] Token retrieved successfully"

# Configure pip to use CodeArtifact
echo "[CodeArtifact Hook] Configuring pip..."

# Create pip configuration directory if it doesn't exist
mkdir -p ~/.pip

# Create pip.conf with CodeArtifact configuration
cat > ~/.pip/pip.conf << EOF
[global]
extra-index-url = https://aws:${AWS_CODEARTIFACT_TOKEN}@${DOMAIN_NAME}-${ACCOUNT_ID}.d.codeartifact.${REGION}.amazonaws.com/pypi/${REPOSITORY_NAME}/simple/
trusted-host = ${DOMAIN_NAME}-${ACCOUNT_ID}.d.codeartifact.${REGION}.amazonaws.com
EOF

echo "[CodeArtifact Hook] Pip configuration created at ~/.pip/pip.conf"

# Also configure for the system-wide pip if needed
if [ -w /etc ]; then
    echo "[CodeArtifact Hook] Configuring system-wide pip..."
    mkdir -p /etc/pip
    cp ~/.pip/pip.conf /etc/pip/pip.conf
    echo "[CodeArtifact Hook] System-wide pip configuration created"
fi

# Set environment variable for this session
export PIP_EXTRA_INDEX_URL="https://aws:${AWS_CODEARTIFACT_TOKEN}@${DOMAIN_NAME}-${ACCOUNT_ID}.d.codeartifact.${REGION}.amazonaws.com/pypi/${REPOSITORY_NAME}/simple/"
export PIP_TRUSTED_HOST="${DOMAIN_NAME}-${ACCOUNT_ID}.d.codeartifact.${REGION}.amazonaws.com"

echo "[CodeArtifact Hook] Environment variables set"
echo "[CodeArtifact Hook] CodeArtifact configuration completed successfully"
