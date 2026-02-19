# Academe Infrastructure - AWS Deployment
# This Terraform configuration deploys:
# - EC2 instance for backend (FastAPI + Celery)
# - Security groups for web access
# - Elastic IP for consistent addressing
# - MongoDB Atlas cluster (free tier)
# - Redis ElastiCache (optional, can use Docker Redis on EC2)

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.15"
    }
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Academe"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# MongoDB Atlas Provider (Optional)
provider "mongodbatlas" {
  public_key  = var.mongodb_atlas_public_key
  private_key = var.mongodb_atlas_private_key
}
