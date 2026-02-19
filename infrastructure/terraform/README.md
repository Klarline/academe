# Terraform Deployment Guide - Academe

## Overview

Deploy Academe to AWS using Terraform for Infrastructure as Code (IaC).

**What Gets Deployed:**
- EC2 instance (t3.small, Ubuntu 22.04)
- Security groups (SSH, HTTP, HTTPS, API)
- Elastic IP (consistent public IP)
- Automated Docker setup with docker-compose
- Nginx reverse proxy
- MongoDB Atlas (free tier, optional)

---

## Prerequisites

### 1. AWS Account Setup
1. Create AWS account: https://aws.amazon.com/
2. Install AWS CLI:
   ```bash
   brew install awscli
   ```

3. Configure AWS credentials:
   ```bash
   aws configure
   # Enter:
   # - AWS Access Key ID
   # - AWS Secret Access Key  
   # - Default region: us-west-2
   # - Output format: json
   ```

### 2. Create SSH Key Pair
```bash
# Create new SSH key for EC2
ssh-keygen -t rsa -b 4096 -f ~/.ssh/academe-key -C "academe-deployment"

# Import to AWS
aws ec2 import-key-pair \
  --key-name academe-key \
  --public-key-material fileb://~/.ssh/academe-key.pub \
  --region us-west-2
```

### 3. Get Your Public IP
```bash
curl ifconfig.me
# Use this for allowed_ssh_cidr variable
```

---

## Step-by-Step Deployment

### Step 1: Configure Terraform Variables

```bash
cd terraform/

# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required values:**
```hcl
# AWS
key_name = "academe-key"  # The key you created
allowed_ssh_cidr = "YOUR_IP/32"  # Your IP from curl ifconfig.me

# Application secrets
google_api_key = "your-google-api-key"
jwt_secret_key = "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Docker Hub
docker_username = "your-dockerhub-username"
docker_password = "your-docker-hub-token"
```

### Step 2: Initialize Terraform

```bash
cd terraform/

# Initialize providers
terraform init

# Should see:
# Terraform has been successfully initialized!
```

### Step 3: Review Deployment Plan

```bash
# See what will be created
terraform plan

# Review output:
# + aws_instance.academe
# + aws_security_group.academe
# + aws_eip.academe
# + mongodbatlas_cluster.academe (if configured)
```

### Step 4: Deploy Infrastructure

```bash
# Apply the configuration
terraform apply

# Review plan and type 'yes' when prompted
# Takes 5-10 minutes
```

### Step 5: Wait for Server Setup

The EC2 instance runs a user-data script that:
1. Installs Docker and Docker Compose
2. Clones your repository
3. Pulls Docker images
4. Starts all services
5. Configures Nginx

**Wait 3-5 minutes after `terraform apply` completes.**

### Step 6: Verify Deployment

```bash
# Get outputs
terraform output

# Test health endpoint
export BACKEND_IP=$(terraform output -raw ec2_public_ip)
curl http://$BACKEND_IP/api/health

# Should return:
# {"status": "healthy", "mongodb": "connected", ...}
```

---

## Accessing Your Deployment

### SSH into Server

```bash
# Get SSH command from Terraform
terraform output ssh_command

# Or manually:
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)
```

### Check Services

```bash
# Once SSH'd in
cd academe
docker-compose ps

# View logs
docker-compose logs -f backend
```

### API Endpoints

```bash
export API_URL=http://$(terraform output -raw ec2_public_ip):8000

# Health check
curl $API_URL/health

# API documentation
open http://$(terraform output -raw ec2_public_ip):8000/docs

# Prometheus metrics
curl $API_URL/metrics
```

---

## Frontend Deployment (Vercel)

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Deploy Frontend

```bash
cd ../frontend

# Login to Vercel
vercel login

# Set environment variable
export BACKEND_URL=$(cd ../terraform && terraform output -raw backend_url)

# Deploy
vercel --prod \
  --env NEXT_PUBLIC_API_URL=$BACKEND_URL \
  --env NEXT_PUBLIC_WS_URL=ws://$(cd ../terraform && terraform output -raw ec2_public_ip):8000
```

---

## MongoDB Atlas Setup (Optional)

If you want to use MongoDB Atlas instead of local MongoDB:

### 1. Create MongoDB Atlas Account
https://www.mongodb.com/cloud/atlas

### 2. Get API Keys
1. Organization Settings → Access Manager → API Keys
2. Create API Key with "Organization Project Creator" permission
3. Save Public Key and Private Key

### 3. Add to terraform.tfvars
```hcl
mongodb_atlas_public_key = "your-public-key"
mongodb_atlas_private_key = "your-private-key"
mongodb_atlas_org_id = "your-org-id"  # From Atlas dashboard
```

### 4. Re-run Terraform
```bash
terraform apply
```

---

## Monitoring & Maintenance

### Check Server Health

```bash
# Health check
curl http://$(terraform output -raw ec2_public_ip)/api/health

# Prometheus metrics
curl http://$(terraform output -raw ec2_public_ip)/metrics

# View logs
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)
cd academe && docker-compose logs -f
```

### Update Deployment

```bash
# SSH into server
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)

# Pull latest code
cd academe
git pull origin main

# Rebuild and restart
docker-compose pull
docker-compose up -d --build

# Check status
docker-compose ps
```

---

## Troubleshooting

### Services not starting?

```bash
# SSH in
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)

# Check user-data script progress
sudo tail -f /var/log/cloud-init-output.log

# Check Docker status
docker-compose ps
docker-compose logs backend
```

### Can't connect to backend?

```bash
# Check security group
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=academe-production"

# Test from server
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)
curl localhost:8000/health
```

### MongoDB connection issues?

```bash
# Check MongoDB Atlas IP whitelist
# Go to Atlas dashboard → Network Access
# Verify EC2 IP is whitelisted

# Test connection from EC2
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)
docker exec -it academe_backend python -c "from pymongo import MongoClient; print(MongoClient('your-connection-string').server_info())"
```

---

## Destroying Infrastructure

When you want to tear down everything:

```bash
cd terraform/

# Preview what will be destroyed
terraform plan -destroy

# Destroy all resources
terraform destroy

# Type 'yes' to confirm
```

---

## Security Best Practices

### 1. Restrict SSH Access
```hcl
# In terraform.tfvars
allowed_ssh_cidr = "YOUR_IP/32"  # Only your IP, not 0.0.0.0/0
```

### 2. Enable HTTPS
After deployment, set up Let's Encrypt:
```bash
ssh -i ~/.ssh/academe-key.pem ubuntu@$(terraform output -raw ec2_public_ip)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 3. Secure Secrets
- Never commit `terraform.tfvars`
- Use AWS Secrets Manager for production
- Rotate JWT secret regularly

### 4. Enable Firewall
```bash
# On EC2
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
