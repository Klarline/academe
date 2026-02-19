# EC2 Instance Configuration

# Get latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# User data script for EC2 initialization
locals {
  # Use MongoDB Atlas if configured, otherwise use local MongoDB in Docker
  mongodb_connection = var.mongodb_atlas_public_key != "" ? mongodbatlas_cluster.academe[0].connection_strings[0].standard_srv : "mongodb://admin:academe123@localhost:27017/?authSource=admin"
  
  user_data = templatefile("${path.module}/user-data.sh", {
    docker_username     = var.docker_username
    docker_password     = var.docker_password
    google_api_key      = var.google_api_key
    jwt_secret_key      = var.jwt_secret_key
    pinecone_api_key    = var.pinecone_api_key
    pinecone_index_name = var.pinecone_index_name
    mongodb_uri         = local.mongodb_connection
  })
}

# EC2 Instance
resource "aws_instance" "academe" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.academe.id]

  user_data = local.user_data

  root_block_device {
    volume_size = 50  # GB - Increased for ML dependencies (torch, transformers, etc.)
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-${var.environment}"
  }
}
