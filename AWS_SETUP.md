# AWS Setup Guide for FaceIT

This guide covers AWS Identity Center (SSO) setup for team members.

## Table of Contents

- [For Team Members: Joining the AWS Account](#for-team-members-joining-the-aws-account)
- [Troubleshooting](#troubleshooting)

---

## For Team Members: Joining the AWS Account

### Step 1: Accept the Email Invitation

You'll receive an email from AWS Identity Center with subject like:
> "Invitation to join AWS IAM Identity Center"

1. Click the **Accept Invitation** button in the email
2. Set up your password (must be at least 8 characters)
3. (Optional) Set up MFA for additional security

### Step 2: Install AWS CLI

**macOS (using Homebrew):**
```bash
brew install awscli
```

**Windows:**
Download from: https://aws.amazon.com/cli/

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify installation:
```bash
aws --version
# Should show: aws-cli/2.x.x or higher
```

### Step 3: Configure AWS SSO

Run the interactive SSO configuration:
```bash
aws configure sso
```

When prompted, enter:

1. **SSO session name:** `faceit-dev` (or any name you prefer)
2. **SSO start URL:** Check Discord for start URL
3. **SSO region:** `us-east-1`
4. **SSO registration scopes:** `sso:account:access` (press Enter for default)

A browser window will open:
- Sign in with the credentials you set up in Step 1
- Click **Allow** to authorize the AWS CLI

Back in the terminal:
5. **Select the AWS account:** Choose the FaceIT account (464011418968)
6. **Select the IAM role:** Choose `DeveloperAccess` or `AdministratorAccess` (depending on what the owner assigned you)
7. **Default region:** `us-east-1`
8. **Default output format:** `json` (press Enter for default)
9. **Profile name:** `admin` (or match what your team is using)

### Step 4: Verify Your Configuration

Check your AWS config file:
```bash
cat ~/.aws/config
```

You should see something like:
```ini
[profile admin]
sso_session = faceit-dev
sso_account_id = 123456789
sso_role_name = DeveloperAccess
region = us-east-1

[sso-session faceit-dev]
sso_start_url = 123456789
sso_region = us-east-1
sso_registration_scopes = sso:account:access
```

### Step 5: Log In and Test

Log in to AWS SSO:
```bash
aws sso login --profile admin
```

This will open a browser for authentication. After successful login, test your access:
```bash
# Set your profile for this session
export AWS_PROFILE=dev

# Test access
aws sts get-caller-identity
```

You should see output with your user ARN and account ID.

## Troubleshooting

### Issue: "SSO session has expired"

**Solution:** Re-login to refresh your session:
```bash
aws sso login --profile dev
```

### Issue: "Error loading SSO Token: Token for [profile] does not exist"

**Solution:** You need to login for the first time:
```bash
aws sso login --profile dev
```

### Issue: "Unable to locate credentials"

**Solution:** Make sure you've set the AWS_PROFILE environment variable:
```bash
export AWS_PROFILE=dev
# Or use --profile flag
aws sts get-caller-identity --profile dev
```

Add to your `~/.zshrc` or `~/.bashrc`:
```bash
export AWS_PROFILE=dev
```

### Issue: "An error occurred (AccessDeniedException)"

**Possible causes:**
1. Your SSO session expired → Run `aws sso login --profile dev`
2. You don't have permission for that action → Ask the owner to update your permission set
3. Wrong AWS account → Verify with `aws sts get-caller-identity`

### Issue: Can't deploy CDK - "Unable to resolve AWS account"

**Solution:** CDK needs an active SSO session:
```bash
aws sso login --profile dev
npx cdk deploy --profile dev
```

### Issue: Browser doesn't open during SSO login

**Solution:** The CLI will print a URL - manually copy and paste it into your browser:
```bash
aws sso login --profile dev
# If browser doesn't open, copy the URL shown and open it manually
```

---

## Best Practices

### For All Team Members

1. **Never commit AWS credentials** to git
   - SSO credentials are stored in `~/.aws/` which is outside the project
   - Never create long-term access keys for this project

2. **Set session duration appropriately**
   - 4 hours is a good default for active development
   - Shorter for production environments

3. **Use `--profile admin` consistently**
   - Or set `AWS_PROFILE=admin` in your shell
   - Prevents accidentally using wrong AWS account

4. **Review resources before deploying**
   - Always run `npx cdk diff --profile admin` before `deploy`
   - Check that changes match your intent

### For Project Owner

1. **Use least privilege**
   - Most team members should have `PowerUserAccess`
   - Only give `AdministratorAccess` to trusted admins

2. **Enable MFA**
   - In Identity Center Settings → MFA
   - Require MFA for sensitive operations

3. **Monitor costs**
   - Check AWS Budgets alerts regularly
   - Review Cost Explorer monthly

4. **Audit access**
   - Periodically review who has access
   - Remove users who left the team

---

## Quick Reference

### Common Commands

```bash
# Login to AWS SSO
aws sso login --profile dev

# Check who you're logged in as
aws sts get-caller-identity --profile dev

# Deploy infrastructure
npx cdk deploy --profile dev

# View resources
aws s3 ls --profile dev
aws sqs list-queues --profile dev

# Logout (rarely needed - session expires automatically)
aws sso logout --profile dev
```

---

## Additional Resources

- [AWS Identity Center Documentation](https://docs.aws.amazon.com/singlesignon/latest/userguide/)
- [AWS CLI SSO Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
