# Output Values

output "ec2_public_ip" {
  description = "Public IP address of EC2 instance"
  value       = aws_eip.academe.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.academe.id
}

output "backend_url" {
  description = "Backend API URL"
  value       = "http://${aws_eip.academe.public_ip}:8000"
}

output "backend_health_url" {
  description = "Backend health check URL"
  value       = "http://${aws_eip.academe.public_ip}/api/health"
}

output "mongodb_connection_string" {
  description = "MongoDB Atlas connection string"
  value       = var.mongodb_atlas_public_key != "" ? mongodbatlas_cluster.academe[0].connection_strings[0].standard_srv : "Using local MongoDB in Docker"
  sensitive   = true
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.academe.public_ip}"
}

output "deployment_summary" {
  description = "Deployment summary"
  value = <<-EOT
  ========================================
  Academe Deployment Complete!
  ========================================
  
  EC2 Instance: ${aws_instance.academe.id}
  Public IP: ${aws_eip.academe.public_ip}
  
  Backend API: http://${aws_eip.academe.public_ip}:8000
  Health Check: http://${aws_eip.academe.public_ip}/api/health
  API Docs: http://${aws_eip.academe.public_ip}:8000/docs
  
  SSH Access: ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.academe.public_ip}
  
  Next Steps:
  1. Wait 3-5 minutes for services to start
  2. Check health: curl http://${aws_eip.academe.public_ip}/api/health
  3. Deploy frontend to Vercel with API_URL=http://${aws_eip.academe.public_ip}:8000
  EOT
}
