# Input Variables for Academe Infrastructure

# AWS Configuration
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "academe"
}

# EC2 Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
  # Upgrade to t3.medium (4GB RAM, ~$30/month) if you need more headroom
}

variable "key_name" {
  description = "SSH key pair name for EC2 access"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH (use your IP/32)"
  type        = string
  default     = "0.0.0.0/0"  # CHANGE THIS to your IP for security!
}

# Application Configuration
variable "google_api_key" {
  description = "Google API key for Gemini"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key (min 32 characters)"
  type        = string
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pinecone_index_name" {
  description = "Pinecone index name"
  type        = string
  default     = "academe-prod"
}

# MongoDB Atlas Configuration (Optional)
variable "mongodb_atlas_public_key" {
  description = "MongoDB Atlas public API key"
  type        = string
  default     = ""
}

variable "mongodb_atlas_private_key" {
  description = "MongoDB Atlas private API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "mongodb_atlas_project_name" {
  description = "MongoDB Atlas project name"
  type        = string
  default     = "Academe"
}

variable "mongodb_atlas_org_id" {
  description = "MongoDB Atlas organization ID"
  type        = string
  default     = ""
}

# Docker Configuration
variable "docker_username" {
  description = "Docker Hub username"
  type        = string
}

variable "docker_password" {
  description = "Docker Hub password or token"
  type        = string
  sensitive   = true
}
