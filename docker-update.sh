echo "Building Docker image and tagging"
docker build -t shorten-gui .
docker tag shorten-gui:latest 638806779113.dkr.ecr.ap-southeast-1.amazonaws.com/shorten-gui:latest

echo "Loggin into ECR"
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 638806779113.dkr.ecr.ap-southeast-1.amazonaws.com
echo "Pusing Image into ECR"
docker push 638806779113.dkr.ecr.ap-southeast-1.amazonaws.com/shorten-gui:latest

echo "Updating ECR Services"
aws ecs update-service --cluster ecs-cluster-singapore --service shorter-gui-svc --force-new-deployment --region ap-southeast-1
echo "Finishing updating ECR Services"
