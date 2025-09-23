#!/bin/bash

# Docker Compose automation script for mono project with AWS CodeArtifact authentication
# Handles authentication, environment setup, and Docker Compose operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ACTION="up"
SERVICES=""
DOCKERFILE="Dockerfile"
COMPOSE_FILE="docker-compose.yml"
ENVIRONMENT="development"
DETACHED=false
BUILD_ONLY=false
PULL=false
NO_CACHE=false
VERBOSE=false

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Usage: $0 [OPTIONS] [COMMAND] [SERVICES...]"
    echo ""
    echo "COMMANDS:"
    echo "  up           Start services (default)"
    echo "  down         Stop and remove services"
    echo "  build        Build services"
    echo "  restart      Restart services"
    echo "  logs         Show service logs"
    echo "  ps           Show running services"
    echo "  exec         Execute command in service"
    echo "  pull         Pull service images"
    echo "  stop         Stop services"
    echo "  start        Start stopped services"
    echo ""
    echo "OPTIONS:"
    echo "  -f, --file FILE          Compose file (default: docker-compose.yml)"
    echo "  -e, --env ENV            Environment (development|production)"
    echo "  -d, --detach             Run in detached mode"
    echo "  -b, --build-only         Only build, don't start services"
    echo "  --pull                   Pull images before building"
    echo "  --no-cache               Build without cache"
    echo "  -v, --verbose            Verbose output"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "SERVICES:"
    echo "  api                      API service only"
    echo "  web-app                  Web app service only"
    echo "  (empty)                  All services"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                       # Start all services in development mode"
    echo "  $0 up api                # Start only API service"
    echo "  $0 build --no-cache      # Rebuild all services without cache"
    echo "  $0 logs api              # Show API logs"
    echo "  $0 exec api bash         # Execute bash in API container"
    echo "  $0 -e production up -d   # Start all services in production mode, detached"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        up|down|build|restart|logs|ps|exec|pull|stop|start)
            ACTION="$1"
            shift
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--detach)
            DETACHED=true
            shift
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        --pull)
            PULL=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        api|web-app)
            SERVICES="$SERVICES $1"
            shift
            ;;
        *)
            # For exec command, capture the command and arguments
            if [ "$ACTION" = "exec" ] && [ -z "$EXEC_SERVICE" ]; then
                EXEC_SERVICE="$1"
                shift
                EXEC_COMMAND="$@"
                break
            else
                print_error "Unknown option or service: $1"
                show_help
                exit 1
            fi
            ;;
    esac
done

# Trim leading spaces from SERVICES
SERVICES=$(echo $SERVICES | sed 's/^ *//')

print_info "Starting Docker Compose automation for mono project"
print_info "Action: $ACTION, Environment: $ENVIRONMENT, Services: ${SERVICES:-all}"

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if docker and docker compose are available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Check if AWS CLI is available and configured for API builds
check_aws_auth() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if [ -z "$AWS_PROFILE" ] && [ -z "$AWS_ACCESS_KEY_ID" ]; then
        print_warning "No AWS credentials found. Make sure you're authenticated with AWS."
        print_info "You can set AWS_PROFILE or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY"
    fi
}

# Get CodeArtifact authentication and create .env file
setup_authentication() {
    print_info "Setting up AWS CodeArtifact authentication..."

    check_aws_auth

    # Get CodeArtifact authentication token
    print_info "Getting AWS CodeArtifact authentication token..."
    CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
        --domain proximal-code-artifact-domain-016997484973 \
        --domain-owner 016997484973 \
        --region us-east-2 \
        --query authorizationToken \
        --output text 2>/dev/null)

    if [ -z "$CODEARTIFACT_AUTH_TOKEN" ]; then
        print_error "Failed to get CodeArtifact authentication token"
        print_error "Please check your AWS credentials and permissions"
        exit 1
    fi

    # Create/update .env file for Docker Compose
    ENV_FILE=".env.docker"
    print_info "Creating environment file: $ENV_FILE"

    cat > "$ENV_FILE" << EOF
# Generated by docker.sh script - $(date)
# AWS CodeArtifact authentication
UV_INDEX_PROXIMAL_USERNAME=aws
UV_INDEX_PROXIMAL_PASSWORD=$CODEARTIFACT_AUTH_TOKEN
CODEARTIFACT_AUTH_TOKEN=$CODEARTIFACT_AUTH_TOKEN

# Environment configuration
ENVIRONMENT=$ENVIRONMENT
COMPOSE_PROJECT_NAME=mono
DOCKER_BUILDKIT=1
BUILDKIT_PROGRESS=plain
EOF

    print_success "Authentication setup completed"
}

# Build services with proper authentication
build_services() {
    print_info "Building services..."

    BUILD_ARGS=""
    if [ "$NO_CACHE" = true ]; then
        BUILD_ARGS="$BUILD_ARGS --no-cache"
    fi

    if [ "$PULL" = true ]; then
        BUILD_ARGS="$BUILD_ARGS --pull"
    fi

    # Set build arguments for authentication
    export UV_INDEX_PROXIMAL_USERNAME=aws
    export UV_INDEX_PROXIMAL_PASSWORD="$CODEARTIFACT_AUTH_TOKEN"

    if [ -n "$SERVICES" ]; then
        print_info "Building specific services: $SERVICES"
        docker compose --env-file .env.docker -f "$COMPOSE_FILE" build $BUILD_ARGS $SERVICES
    else
        print_info "Building all services"
        docker compose --env-file .env.docker -f "$COMPOSE_FILE" build $BUILD_ARGS
    fi

    print_success "Build completed"
}

# Execute Docker Compose commands
execute_compose_command() {
    local cmd_args=""

    case $ACTION in
        up)
            if [ "$DETACHED" = true ]; then
                cmd_args="$cmd_args -d"
            fi
            cmd_args="$cmd_args --build"
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" up $cmd_args $SERVICES
            ;;
        down)
            cmd_args="--remove-orphans"
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" down $cmd_args $SERVICES
            ;;
        restart)
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" restart $SERVICES
            ;;
        logs)
            cmd_args="-f"
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" logs $cmd_args $SERVICES
            ;;
        ps)
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" ps $SERVICES
            ;;
        exec)
            if [ -z "$EXEC_SERVICE" ]; then
                print_error "Service name required for exec command"
                exit 1
            fi
            if [ -z "$EXEC_COMMAND" ]; then
                EXEC_COMMAND="bash"
            fi
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" exec "$EXEC_SERVICE" $EXEC_COMMAND
            ;;
        pull)
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" pull $SERVICES
            ;;
        stop)
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" stop $SERVICES
            ;;
        start)
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" start $SERVICES
            ;;
        build)
            build_services
            return
            ;;
        *)
            print_error "Unknown action: $ACTION"
            exit 1
            ;;
    esac
}

# Main execution flow
main() {
    # Always setup authentication for API service
    setup_authentication

    if [ "$BUILD_ONLY" = true ] || [ "$ACTION" = "build" ]; then
        build_services
        exit 0
    fi

    # Execute the requested Docker Compose command
    print_info "Executing Docker Compose command: $ACTION"
    execute_compose_command

    # Show status after certain commands
    case $ACTION in
        up|start|restart)
            echo ""
            print_info "Service status:"
            docker compose --env-file .env.docker -f "$COMPOSE_FILE" ps

            if [ "$ACTION" = "up" ] && [ "$DETACHED" = false ]; then
                echo ""
                print_info "Services started. Press Ctrl+C to stop."
            else
                echo ""
                print_success "Services are running in the background"
                print_info "Use '$0 logs' to view logs"
                print_info "Use '$0 down' to stop services"
            fi
            ;;
        down|stop)
            print_success "Services stopped"
            ;;
    esac
}

# Cleanup function
cleanup() {
    print_info "Cleaning up temporary files..."
    if [ -f ".env.docker" ]; then
        rm -f .env.docker
    fi
}

# Set up trap for cleanup
trap cleanup EXIT

# Run main function
main

print_success "Docker operations completed successfully"
