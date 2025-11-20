#!/bin/bash

echo "=== TESTS ==="

# 1. Test Ansible installation
echo "1. Check Ansible..."
docker exec api ansible --version

# 2. Test playbook rotation
echo "2. Test rotation playbook..."
docker exec api ansible-playbook /ansible/playbooks/rotate-mysql.yml

# 3. Test API Ansible endpoints
echo "3. Test API endpoints..."
curl -X POST http://localhost:5000/ansible/rotate | jq
curl -X GET http://localhost:5000/ansible/health | jq

# 4. Test automation script
echo "4. Test automation..."
./demo/automation.sh all

# 5. Check logs
echo "5. Check logs..."
ls -la logs/
tail -n 10 logs/rotations.log
tail -n 10 logs/certificates.log

echo "Tests completed!"