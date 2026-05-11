# cmms-integration-fetcher

Defines AWS Lambda that fetches CMMS integrations to pass to cmms-ticket-download lambda

# Docker Deployment to Lambda

## Image Creation


### Test Locally (optional)

```bash
 docker buildx build --platform linux/arm64 --provenance=false --load -f microservices/cmms-integration-fetcher/Dockerfile -t docker-image:test .
```

```bash
docker run --rm --platform linux/arm64 -p 9000:8080 \
    -e AWS_REGION=us-east-2 \
    -v "$HOME/.aws:/root/.aws:ro" \
    docker-image:test
```

In a separate terminal run

```bash
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"backfill_days": 3}'
```

Then kill the initial process.

## Export to ECR

### 1\. Authenticate Docker to AWS ECR

First, you need to allow your local Docker client to authenticate with your AWS ECR registry. This is done using the AWS Command Line Interface (CLI). If you don't have the AWS CLI installed and configured, you'll need to do that first.

Once the AWS CLI is ready, run the following command in your terminal.

```bash
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <your_aws_account_id>.dkr.ecr.us-east-2.amazonaws.com
```

You will need to replace `<your_aws_account_id>` with your actual AWS account ID. If successful, you will see a "Login Succeeded" message.

### 2\. Create an ECR Repository

If note created already, you need a repository in ECR to store your image. You can create one using the AWS CLI with the following command. Replace `your-repo-name` with the desired name for your repository.

```bash
aws ecr create-repository --repository-name <your-repo-name> --region us-east-2
```

Upon successful creation, the output will be a JSON object containing details about your new repository, including the `repositoryUri`, which you will need in the next step.

### 3\. Tag Your Docker Image

Now, you need to tag your local Docker image with the ECR repository URI. This tells Docker where to push the image. Use the `docker tag` command as follows, replacing the placeholders with your image's name and tag, and your repository URI.

```bash
docker tag your-image-name:tag <your_aws_account_id>.dkr.ecr.us-east-2.amazonaws.com/<your-repo-name>:tag
```

For example, if your local image is named `my-lambda-image:latest` and your repository URI is `123456789012.dkr.ecr.us-east-2.amazonaws.com/my-lambda-repo`, the command would be:

```bash
docker tag my-lambda-image:latest 123456789012.dkr.ecr.us-east-2.amazonaws.com/my-lambda-repo:latest
```

### 4\. Push the Image to ECR

Finally, you can push your tagged image to your ECR repository using the `docker push` command.

```bash
docker push <your_aws_account_id>.dkr.ecr.us-east-2.amazonaws.com/your-repo-name:tag
```

Once the push is complete, your Lambda Docker image will be available in your ECR repository, ready to be deployed to AWS Lambda.

## Deploy Lambda Function

### 1\. Create Lambda From Scratch

```
aws lambda create-function --function-name <lambda-name> --package-type Image --code ImageUri=<image-uri> --architectures arm64 --role <arn-role-name>
```

I'm using the AWSLambda_ReadOnlyAccess_ECR role for my lambda functions.

### Or Update Lambda

```bash
aws lambda update-function-code \
  --function-name hello-world \
  --image-uri 111122223333.dkr.ecr.us-east-1.amazonaws.com/hello-world:latest \
  --publish
```

### 2.\ Test it

```bash
aws lambda invoke --function-name <lambda-name> --payload '{"json": "event_data"}' --cli-binary-format raw-in-base64-out /dev/stdout
```
