#!/bin/bash

# Development environment shortcuts for mono project
# This script provides convenient commands for common development tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[DEV]${NC} $1"
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
    echo "Development shortcuts for mono project"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "COMMANDS:"
    echo "  start, up        Start all services in development mode"
    echo "  stop, down       Stop all services"
    echo "  restart          Restart all services"
    echo "  build            Build all services"
    echo "  rebuild          Rebuild all services without cache"
    echo "  logs             Follow logs for all services"
    echo "  api-logs         Show API logs only"
    echo "  web-logs         Show web app logs only"
    echo "  api-shell        Open bash shell in API container"
    echo "  api-python       Open Python shell in API container"
    echo "  web-shell        Open bash shell in web app container"
    echo "  status, ps       Show service status"
    echo "  clean            Clean up containers, images, and volumes"
    echo "  reset            Full reset - clean and rebuild everything"
    echo "  help             Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 start         # Start development environment"
    echo "  $0 api-shell     # Open shell in API container"
    echo "  $0 rebuild       # Rebuild everything without cache"
    echo "  $0 reset         # Complete reset and restart"
}

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_SCRIPT="$SCRIPT_DIR/docker.sh"

# Ensure docker.sh exists and is executable
if [ ! -f "$DOCKER_SCRIPT" ]; then
    print_error "docker.sh not found at $DOCKER_SCRIPT"
    exit 1
fi

if [ ! -x "$DOCKER_SCRIPT" ]; then
    print_warning "Making docker.sh executable..."
    chmod +x "$DOCKER_SCRIPT"
fi

# Parse command
COMMAND="${1:-help}"

case $COMMAND in
    start|up)
        print_info "Starting development environment..."
        "$DOCKER_SCRIPT" up
        ;;

    stop|down)
        print_info "Stopping all services..."
        "$DOCKER_SCRIPT" down
        ;;

    restart)
        print_info "Restarting all services..."
        "$DOCKER_SCRIPT" restart
        ;;

    build)
        print_info "Building all services..."
        "$DOCKER_SCRIPT" build
        ;;

    rebuild)
        print_info "Rebuilding all services without cache..."
        "$DOCKER_SCRIPT" build --no-cache
        ;;

    logs)
        print_info "Following logs for all services..."
        "$DOCKER_SCRIPT" logs
        ;;

    api-logs)
        print_info "Showing API logs..."
        "$DOCKER_SCRIPT" logs api
        ;;

    web-logs)
        print_info "Showing web app logs..."
        "$DOCKER_SCRIPT" logs web-app
        ;;

    api-shell)
        print_info "Opening bash shell in API container..."
        "$DOCKER_SCRIPT" exec api bash
        ;;

    api-python)
        print_info "Opening Python shell in API container..."
        "$DOCKER_SCRIPT" exec api uv run python
        ;;

    web-shell)
        print_info "Opening bash shell in web app container..."
        "$DOCKER_SCRIPT" exec web-app bash
        ;;

    status|ps)
        print_info "Service status:"
        "$DOCKER_SCRIPT" ps
        ;;

    clean)
        print_warning "Cleaning up containers, images, and volumes..."
        read -p "Are you sure? This will remove stopped containers, unused images, and volumes. [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Stopping services..."
            "$DOCKER_SCRIPT" down || true

            print_info "Cleaning up Docker resources..."
            docker system prune -f --volumes
            print_success "Cleanup completed"
        else
            print_info "Cleanup cancelled"
        fi
        ;;

    reset)
        print_warning "Performing full reset - this will rebuild everything from scratch..."
        read -p "Are you sure? This will stop services, clean up, and rebuild. [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Stopping services..."
            "$DOCKER_SCRIPT" down || true

            print_info "Cleaning up Docker resources..."
            docker system prune -f --volumes

            print_info "Rebuilding all services..."
            "$DOCKER_SCRIPT" build --no-cache

            print_info "Starting services..."
            "$DOCKER_SCRIPT" up -d

            print_success "Full reset completed"
            print_info "Services are now running in the background"
        else
            print_info "Reset cancelled"
        fi
        ;;

    help|-h|--help)
        show_help
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
