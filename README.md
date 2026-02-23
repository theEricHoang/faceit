# FaceIT

Facial recognition-based attendance system with FastAPI backend, Expo/React Native frontend, and AWS infrastructure.

## Project Structure

```
faceit/
├── backend/          # FastAPI + Supabase backend
├── frontend/         # Expo/React Native mobile app
├── infra/            # AWS CDK infrastructure (TypeScript)
├── DESIGN.md         # Architecture and design decisions
└── AGENTS.md         # Coding guidelines for AI agents
```

## Quick Start

### Prerequisites

- **Node.js** 20+ (for frontend and infra)
- **Python** 3.12.2 (for backend)
- **AWS CLI** with SSO configured (for infrastructure)
- **Supabase** account

### Backend Setup

```bash
cd backend/

# Create Python virtual environment
pyenv install 3.12.2
pyenv virtualenv 3.12.2 backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# Run development server
uvicorn app.main:app --host 0.0.0.0 --reload

# Run tests
pytest tests/ -v
```

### Frontend Setup

```bash
cd frontend/

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API URL

# Start development server
npx expo start

# Run on specific platform
npm run ios       # iOS simulator
npm run android   # Android emulator
npm run web       # Web browser
```

### Infrastructure Setup

```bash
cd infra/

# Install dependencies
npm install

# Configure AWS SSO (see AWS_SETUP.md for details)
aws configure sso

# Bootstrap CDK (one-time)
npx cdk bootstrap --profile dev

# Deploy infrastructure
npx cdk deploy --profile dev
```

**See [AWS_SETUP.md](./AWS_SETUP.md) for detailed AWS Identity Center setup instructions for team members.**

## Team Onboarding

### For New Developers

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd faceit
   ```

2. **Request AWS access** from the project owner
   - You'll receive an email invitation to AWS Identity Center
   - Follow the email instructions to set up your password

3. **Configure AWS SSO** (see [AWS_SETUP.md](./AWS_SETUP.md))
   ```bash
   aws configure sso
   ```

4. **Set up backend and frontend** (see Quick Start above)

### For Project Owner (First-Time AWS Setup)

If you haven't already set up AWS Identity Center for your team:
- See [AWS_SETUP.md](./AWS_SETUP.md) section "Setting Up AWS Identity Center for Your Team"

## Development Workflow

### Running Locally

**Terminal 1 - Backend:**
```bash
cd backend/
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend/
npx expo start
```

### Testing

**Backend:**
```bash
cd backend/
pytest tests/ -v
pytest tests/services/test_auth_service.py -v  # Single file
```

**Frontend:**
```bash
cd frontend/
npm run lint
```

**Infrastructure:**
```bash
cd infra/
npm test
```

## Documentation

- **[DESIGN.md](./DESIGN.md)** - Architecture, data flow, AWS design
- **[AGENTS.md](./AGENTS.md)** - Code style guidelines
- **[AWS_SETUP.md](./AWS_SETUP.md)** - AWS Identity Center team setup
- **[backend/README.md](./backend/README.md)** - Backend details
- **[frontend/README.md](./frontend/README.md)** - Frontend details
- **[infra/README.md](./infra/README.md)** - Infrastructure deployment

## Tech Stack

### Backend
- **FastAPI** - Web framework
- **Supabase** - Auth + PostgreSQL database
- **Python 3.12.2** - Runtime
- **pytest** - Testing

### Frontend
- **Expo SDK 54** - React Native framework
- **React 19** - UI library
- **Zustand** - State management
- **expo-router** - File-based routing
- **TypeScript** - Type safety

### Infrastructure
- **AWS CDK** - Infrastructure as code
- **S3** - Temporary image storage
- **SQS** - Job queues
- **IAM** - Access control
- **Budgets** - Cost management

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Create a pull request

## Cost Management

- AWS budget set to $5/month with alerts at 50%, 80%, 100%
- S3 lifecycle deletes images after 1 day
- Expected cost: ~$0.01/month at current usage (2-3 uploads/day)

## Support

For questions or issues:
- Check the relevant README in backend/, frontend/, or infra/
- Review DESIGN.md for architecture questions
- Review AGENTS.md for code style guidelines
