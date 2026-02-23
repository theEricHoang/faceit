# FaceIT Infrastructure (AWS CDK)

AWS infrastructure as code for FaceIT using CDK with TypeScript.

## Resources Provisioned

- **S3 Bucket**: `faceit-uploads-dev` with 1-day lifecycle deletion for enrollment and class photos
- **SQS Queues**: Enrollment and attendance queues with attached DLQs
- **IAM Roles**: 
  - API role for EC2 instance profile (future use)
  - Worker task execution role for ECS (future use)
  - Worker task role for ECS (future use)
- **AWS Budget**: $5/month with 50%, 80%, 100% alerts

## Prerequisites

1. **AWS CLI** configured with SSO:
   ```bash
   aws configure sso
   # Follow prompts to configure your SSO profile
   ```

2. **Node.js** v20+ and npm (already installed)

3. **CDK CLI** (optional, can use `npx cdk`):
   ```bash
   npm install -g aws-cdk
   ```

## Setup

1. **Install dependencies** (if not already done):
   ```bash
   npm install
   ```

2. **Create AWS Budget Alert Email Secret** (one-time setup):
   
   Store your email address in AWS Secrets Manager for budget alerts:
   ```bash
   aws secretsmanager create-secret \
     --name faceit/dev/budget-alert-email \
     --description "Email address for AWS budget alerts" \
     --secret-string '{"email":"your-email@example.com"}' \
     --profile your-sso-profile \
     --region us-east-1
   ```
   
   Replace `your-email@example.com` with your actual email address.
   
   **Why Secrets Manager?** This keeps your email out of the codebase while allowing CDK to reference it securely.

3. **Bootstrap CDK** (one-time setup per AWS account/region):
   ```bash
   npx cdk bootstrap --profile your-sso-profile
   ```
   
   This creates the CDKToolkit CloudFormation stack with an S3 bucket for assets.

## Development

### Build
```bash
npm run build
```

### Run Tests
```bash
npm test
```

### Watch Mode (auto-compile on changes)
```bash
npm run watch
```

## Deployment

### Preview Changes
```bash
npx cdk diff --profile your-sso-profile
```

### Deploy to AWS
```bash
npx cdk deploy --profile your-sso-profile
```

After successful deployment, CDK will output important values like:
- S3 bucket name
- SQS queue URLs
- IAM role ARNs

**Save these outputs** - you'll need them for backend configuration.

### Synthesize CloudFormation Template (optional)
```bash
npx cdk synth --profile your-sso-profile
```

## Post-Deployment: Backend Integration

After deploying infrastructure, update your backend configuration:

1. **Add AWS SDK to backend**:
   ```bash
   cd ../backend
   echo "boto3==1.35.84" >> requirements.txt
   pip install boto3
   ```

2. **Configure AWS credentials for local dev**:
   
   Your backend will use your SSO credentials automatically via boto3.
   
   Ensure your SSO session is active:
   ```bash
   aws sso login --profile your-sso-profile
   ```

3. **Update `backend/.env`** with CDK outputs:
   ```bash
   # AWS Configuration
   AWS_REGION=us-east-1
   
   # S3 Bucket (from CDK output)
   S3_BUCKET_NAME=faceit-uploads-dev
   
   # SQS Queue URLs (from CDK output)
   SQS_ENROLLMENT_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../faceit-enrollment-queue
   SQS_ATTENDANCE_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../faceit-attendance-queue
   ```

4. **For EC2 deployment** (future):
   
   When deploying FastAPI to EC2, attach the `faceit-api-role-dev` instance profile to the EC2 instance. The backend will automatically use the instance role instead of SSO credentials.

## Verification

After deployment, verify resources were created correctly:

```bash
# Set your AWS profile
export AWS_PROFILE=your-sso-profile

# Verify S3 bucket
aws s3api get-bucket-lifecycle-configuration --bucket faceit-uploads-dev

# Verify SQS queues
aws sqs list-queues | grep faceit

# Verify IAM roles
aws iam get-role --role-name faceit-api-role-dev
aws iam get-role --role-name faceit-worker-role-dev

# Verify budget
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text)
```

## Budget Alert Configuration

The budget is created with a placeholder email (`email@example.com`). To receive alerts:

1. **Option A**: Update the budget in AWS Console:
   - Go to AWS Billing Console → Budgets
   - Edit the `faceit-dev-monthly-budget`
   - Update subscriber email addresses

2. **Option B**: Update `lib/faceit-dev-stack.ts`:
   - Set `alertEmail` parameter in the `BudgetConstruct`
   - Run `npx cdk deploy` again

## Cleanup

To destroy all resources (⚠️ use with caution):

```bash
npx cdk destroy --profile your-sso-profile
```

**Note**: The S3 bucket has a `RETAIN` policy and won't be automatically deleted. You must manually delete it in the AWS Console if desired.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FaceIT AWS Stack                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────┐   ┌──────────────────────────────┐  │
│  │  S3 Bucket    │   │      SQS Queues              │  │
│  │               │   │                              │  │
│  │ • 1-day TTL   │   │ • faceit-enrollment-queue    │  │
│  │ • Encrypted   │   │ • faceit-attendance-queue    │  │
│  │ • No public   │   │ • DLQs attached              │  │
│  │   access      │   │ • 300s visibility timeout    │  │
│  └───────────────┘   └──────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              IAM Roles                           │  │
│  │                                                  │  │
│  │ • faceit-api-role-dev (EC2)                     │  │
│  │ • faceit-worker-role-dev (ECS task)             │  │
│  │ • faceit-worker-execution-role-dev (ECS exec)   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────┐                                     │
│  │  AWS Budget   │                                     │
│  │               │                                     │
│  │ • $5/month    │                                     │
│  │ • Email alerts│                                     │
│  └───────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### CDK Bootstrap Issues
If bootstrap fails, ensure your SSO session is active:
```bash
aws sso login --profile your-sso-profile
```

### Permission Errors During Deployment
Verify your SSO user has `AdministratorAccess` or permissions to create:
- S3 buckets
- SQS queues
- IAM roles
- CloudFormation stacks
- AWS Budgets

### Tests Failing
Ensure dependencies are installed and TypeScript compiles:
```bash
npm install
npm run build
npm test
```

## CDK Commands Reference

* `npm run build`   - Compile TypeScript to JavaScript
* `npm run watch`   - Watch for changes and auto-compile
* `npm run test`    - Run Jest unit tests
* `npx cdk deploy`  - Deploy this stack to AWS
* `npx cdk diff`    - Compare deployed stack with current state
* `npx cdk synth`   - Emit synthesized CloudFormation template
* `npx cdk destroy` - Remove all resources from AWS
