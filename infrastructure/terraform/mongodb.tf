# MongoDB Atlas Cluster Configuration

# Create MongoDB Atlas Project
resource "mongodbatlas_project" "academe" {
  count = var.mongodb_atlas_public_key != "" ? 1 : 0
  
  name   = var.mongodb_atlas_project_name
  org_id = var.mongodb_atlas_org_id
}

# Create Free Tier MongoDB Cluster
resource "mongodbatlas_cluster" "academe" {
  count = var.mongodb_atlas_public_key != "" ? 1 : 0
  
  project_id = mongodbatlas_project.academe[0].id
  name       = "${var.project_name}-${var.environment}"

  # Free tier configuration
  provider_name               = "TENANT"
  backing_provider_name       = "AWS"
  provider_region_name        = "US_WEST_2"
  provider_instance_size_name = "M0"  # Free tier

  # Auto-scaling disabled for free tier
  auto_scaling_disk_gb_enabled = false
}

# Database user
resource "mongodbatlas_database_user" "academe" {
  count = var.mongodb_atlas_public_key != "" ? 1 : 0
  
  username           = "academe"
  password           = random_password.mongodb_password[0].result
  project_id         = mongodbatlas_project.academe[0].id
  auth_database_name = "admin"

  roles {
    role_name     = "readWrite"
    database_name = "academe"
  }

  roles {
    role_name     = "dbAdmin"
    database_name = "academe"
  }
}

# Network access - Allow from EC2
resource "mongodbatlas_project_ip_access_list" "academe" {
  count = var.mongodb_atlas_public_key != "" ? 1 : 0
  
  project_id = mongodbatlas_project.academe[0].id
  ip_address = aws_eip.academe.public_ip
  comment    = "Academe EC2 instance"
}

# Generate secure MongoDB password
resource "random_password" "mongodb_password" {
  count   = var.mongodb_atlas_public_key != "" ? 1 : 0
  
  length  = 32
  special = true
}
