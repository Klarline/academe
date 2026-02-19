#!/bin/bash
# Monitor Academe Deployment Progress

IP="54.200.230.109"

echo "Monitoring Academe Deployment"
echo "================================"
echo "IP: $IP"
echo ""

# Check if services are running
check_services() {
    echo "Checking Docker services..."
    ssh -i ~/.ssh/academe-key -o StrictHostKeyChecking=no ubuntu@$IP \
        "cd academe/infrastructure/docker 2>/dev/null && docker-compose ps" 2>&1 | grep -v "Warning:"
}

# Check health endpoint
check_health() {
    echo ""
    echo "Checking health endpoint..."
    curl -s http://$IP/api/health 2>&1 | head -5
}

# Check setup progress
check_setup() {
    echo ""
    echo "Setup progress (last 20 lines)..."
    ssh -i ~/.ssh/academe-key -o StrictHostKeyChecking=no ubuntu@$IP \
        "tail -20 /var/log/cloud-init-output.log" 2>&1 | grep -v "Warning:"
}

# Main monitoring loop
while true; do
    clear
    echo "Academe Deployment Monitor"
    echo "=============================="
    echo "Time: $(date)"
    echo ""
    
    check_services
    check_health
    
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    echo "Refreshing in 30 seconds..."
    
    sleep 30
done
