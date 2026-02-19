#!/bin/bash
# Quick Terraform Deployment Script

set -e

echo "Academe Terraform Deployment"
echo "================================"

# Check prerequisites
echo ""
echo "Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    echo "Terraform not installed"
    echo "Install: brew install terraform"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "AWS CLI not installed"
    echo "Install: brew install awscli"
    exit 1
fi

echo "Terraform installed: $(terraform version | head -1)"
echo "AWS CLI installed: $(aws --version)"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

echo "AWS credentials configured"

# Navigate to terraform directory
cd "$(dirname "$0")/../terraform"

# Check if terraform.tfvars exists
if [ ! -f terraform.tfvars ]; then
    echo ""
    echo "   terraform.tfvars not found!"
    echo ""
    echo "Please create terraform.tfvars from the example:"
    echo "  cp terraform.tfvars.example terraform.tfvars"
    echo "  nano terraform.tfvars"
    echo ""
    echo "Required variables:"
    echo "  - key_name (SSH key pair name)"
    echo "  - allowed_ssh_cidr (your IP/32)"
    echo "  - google_api_key"
    echo "  - jwt_secret_key"
    echo "  - docker_username"
    echo "  - docker_password"
    exit 1
fi

echo "terraform.tfvars found"

# Initialize Terraform (if not already done)
if [ ! -d .terraform ]; then
    echo ""
    echo "Initializing Terraform..."
    terraform init
fi

# Validate configuration
echo ""
echo "Validating configuration..."
if terraform validate; then
    echo "Configuration valid"
else
    echo "Configuration invalid"
    exit 1
fi

# Show deployment plan
echo ""
echo "========================================="
echo "Deployment Plan"
echo "========================================="
terraform plan

# Confirm deployment
echo ""
read -p "Do you want to deploy? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Apply configuration
echo ""
echo "Deploying infrastructure..."
terraform apply -auto-approve

# Show outputs
echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
terraform output deployment_summary

echo ""
echo "Important Information:"
echo "  Public IP: $(terraform output -raw ec2_public_ip)"
echo "  SSH: $(terraform output -raw ssh_command)"
echo ""
echo "Wait 3-5 minutes for services to start, then:"
echo "  curl http://$(terraform output -raw ec2_public_ip)/api/health"
