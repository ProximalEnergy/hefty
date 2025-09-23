# Docker Setup Guide for Mono Project

Complete guide for running the mono project using Docker Compose with AWS CodeArtifact authentication for the core library.

## Quick Start

The fastest way to get started:

```bash
# Start development environment
./_scripts/dev.sh start

# Or use the Docker script directly
./_scripts/docker.sh up
```

## Prerequisites

1. **Docker & Docker Compose** - Latest version recommended
2. **AWS CLI** - For CodeArtifact authentication
3. **AWS Credentials** - Configured via profile or environment variables
4. **Access** - To the AWS CodeArtifact repository `proximal-code-artifact-domain-016997484973`

## Scripts Overview

### `_scripts/docker.sh` - Main Docker Automation Script

Full-featured script that handles:
- AWS CodeArtifact authentication
- Environment variable management  
- Docker Compose operations
- Build management with authentication

### `_scripts/dev.sh` - Development Shortcuts

Convenience wrapper providing simple commands for common development tasks.

## Available Commands

### Development Shortcuts (`dev.sh`)

```bash
# Start/Stop
./_scripts/dev.sh start     # Start all services
./_scripts/dev.sh stop      # Stop all services
./_scripts/dev.sh restart   # Restart services

# Building
./_scripts/dev.sh build     # Build all services
./_scripts/dev.sh rebuild   # Build without cache

# Logs
./_scripts/dev.sh logs      # Follow all logs
./_scripts/dev.sh api-logs  # API logs only
./_scripts/dev.sh web-logs  # Web app logs only

# Shell Access
./_scripts/dev.sh api-shell    # Bash in API container
./_scripts/dev.sh api-python   # Python shell in API
./_scripts/dev.sh web-shell    # Bash in web container

# Maintenance
./_scripts/dev.sh status    # Show service status
./_scripts/dev.sh clean     # Clean up Docker resources
./_scripts/dev.sh reset     # Full reset and rebuild
```

### Full Docker Script (`docker.sh`)

```bash
# Basic Operations
./_scripts/docker.sh up                    # Start services
./_scripts/docker.sh up api               # Start API only
./_scripts/docker.sh up -d                # Start in background
./_scripts/docker.sh down                 # Stop and remove
./_scripts/docker.sh restart              # Restart services

# Building
./_scripts/docker.sh build                # Build all services
./_scripts/docker.sh build --no-cache     # Build without cache
./_scripts/docker.sh build --pull         # Pull base images first
./_scripts/docker.sh build api            # Build API only

# Logs and Status
./_scripts/docker.sh logs                 # Follow logs
./_scripts/docker.sh logs api             # API logs only
./_scripts/docker.sh ps                   # Show status

# Container Access
./_scripts/docker.sh exec api bash        # Shell in API
./_scripts/docker.sh exec api uv run python  # Python in API
./_scripts/docker.sh exec web-app npm run dev # Command in web-app

# Advanced Options
./_scripts/docker.sh -e production up -d  # Production mode
./_scripts/docker.sh -f custom.yml up     # Custom compose file
./_scripts/docker.sh -v up                # Verbose output
```

## How Authentication Works

The script automatically:

1. **Checks AWS credentials** - Via profile or environment variables
2. **Gets CodeArtifact token** - Valid for 12 hours
3. **Creates `.env.docker`** - Temporary file with authentication
4. **Passes to Docker** - As build arguments for private repository access
5. **Cleans up** - Removes temporary files after operation

### Authentication Setup

#### Option 1: AWS Profile
```bash
aws configure --profile your-profile
export AWS_PROFILE=your-profile
```

#### Option 2: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-2
```

#### Option 3: AWS SSO
```bash
aws sso login --profile your-sso-profile
export AWS_PROFILE=your-sso-profile
```

## Services

### API Service
- **Port**: 8000
- **Health Check**: `http://localhost:8000/health`
- **Hot Reload**: Enabled in development
- **Core Library**: Automatically installed with authentication

### Web App Service
- **Port**: 5173
- **Hot Reload**: Enabled in development
- **API Connection**: `http://localhost:8000`

## Development Workflow

### Daily Development
```bash
# Start everything
./_scripts/dev.sh start

# View logs
./_scripts/dev.sh logs

# Access API shell for debugging
./_scripts/dev.sh api-shell

# Stop when done
./_scripts/dev.sh stop
```

### After Dependency Changes
```bash
# Rebuild with updated dependencies
./_scripts/dev.sh rebuild

# Or just the API if core library updated
./_scripts/docker.sh build api
```

### Debugging Issues
```bash
# Check service status
./_scripts/dev.sh status

# View specific service logs
./_scripts/dev.sh api-logs

# Access container for investigation
./_scripts/dev.sh api-shell

# Full reset if needed
./_scripts/dev.sh reset
```

## Configuration

### Environment Variables

The scripts create a temporary `.env.docker` file with:
- `UV_INDEX_PROXIMAL_USERNAME=aws`
- `UV_INDEX_PROXIMAL_PASSWORD=<token>`
- `ENVIRONMENT=development`
- `COMPOSE_PROJECT_NAME=mono`

### Docker Compose Configuration

Services are configured for development with:
- **Volume mounting** for hot reload
- **Health checks** for reliability
- **Watch mode** for automatic rebuilds
- **Network isolation** with custom bridge

## Troubleshooting

### Common Issues

**"Failed to get CodeArtifact authentication token"**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify CodeArtifact access permissions
- Ensure correct region (us-east-2)

**"Package not found" during build**
- Verify `core` library version in `pyproject.toml`
- Check token hasn't expired (12-hour limit)
- Try rebuilding: `dev.sh rebuild`

**"Permission denied"**
- Ensure scripts are executable: `chmod +x _scripts/*.sh`
- Check Docker daemon is running
- Verify user is in docker group (Linux)

**Port already in use**
- Stop existing services: `dev.sh stop`
- Check for other processes: `lsof -i :8000`
- Use different ports in docker-compose.yml

### Docker Issues

**Build cache problems**
```bash
./_scripts/dev.sh rebuild  # Rebuild without cache
```

**Storage space issues**
```bash
./_scripts/dev.sh clean    # Clean up unused resources
docker system df           # Check disk usage
```

**Network issues**
```bash
./_scripts/docker.sh down  # Stop services
docker network prune       # Clean networks
./_scripts/docker.sh up    # Restart
```

### Logs and Debugging

**View all logs**
```bash
./_scripts/dev.sh logs
```

**Debug API startup**
```bash
./_scripts/dev.sh api-logs
./_scripts/dev.sh api-shell
# Inside container:
uv run python -c "import app.main; print('API module loads correctly')"
```

**Check core library installation**
```bash
./_scripts/dev.sh api-shell
# Inside container:
uv run python -c "import core; print(core.__version__)"
```

## Production Deployment

For production environments:

```bash
# Build for production
./_scripts/docker.sh -e production build

# Start in production mode
./_scripts/docker.sh -e production up -d

# Check status
./_scripts/docker.sh ps
```

## Security Notes

- 🔒 **Authentication tokens** are temporary (12 hours)
- 🔒 **No credentials** stored in Docker images
- 🔒 **`.env.docker`** automatically cleaned up
- 🔒 **Tokens not committed** to version control (gitignored)
- 🔒 **BuildKit secrets** used for secure credential mounting

## Performance Tips

- Use `--build` flag sparingly in production
- Leverage Docker layer caching
- Use `.dockerignore` to exclude unnecessary files
- Consider multi-stage builds for smaller images
- Monitor resource usage with `docker stats`

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v2
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-2

- name: Build and test
  run: |
    ./_scripts/docker.sh build
    ./_scripts/docker.sh up -d
    # Run tests
    ./_scripts/docker.sh down
```

## Support

For issues with:
- **Docker setup**: Check this guide's troubleshooting section
- **AWS authentication**: Verify AWS credentials and permissions
- **Core library**: Check version compatibility in `pyproject.toml`
- **Development workflow**: Use `dev.sh help` for available commands

## File Structure

```
mono/
├── _scripts/
│   ├── docker.sh          # Main Docker automation
│   └── dev.sh             # Development shortcuts
├── api/
│   ├── Dockerfile         # API container definition
│   ├── pyproject.toml     # Python dependencies
│   └── uv.lock           # Locked dependencies
├── web-app/
│   └── Dockerfile         # Web app container
├── docker-compose.yml     # Service orchestration
└── DOCKER_README.md       # This file
```
