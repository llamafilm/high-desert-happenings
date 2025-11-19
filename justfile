export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473 .


# Default command to list all available commands.
default:
    @just --list

# build: Build python image.
build:
    @echo "Building python image..."
    @docker compose build

# up: Start up containers.
up:
    @echo "Starting up containers..."
    @docker compose up -d --remove-orphans

# down: Stop containers.
down:
    @echo "Stopping containers..."
    @docker compose down

# restart: Restart containers.
restart:
    @echo "Restarting containers..."
    @docker compose restart

# prune: Remove containers and their volumes.
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs
logs *args:
    @docker compose logs -f {{args}}

# manage: Executes `manage.py` command.
manage +args:
    @docker compose run --rm django python ./manage.py {{args}}

# Connect to Postgres database inside container
psql:
    @docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'

# deps: Update uv lock file with dependencies from pyproject.toml
deps:
    @docker compose run --rm django uv lock

# Create or sync the virtual environment using uv
venv:
    @uv sync --no-install-project
    @echo "Virtual environment created. Activate it with: source .venv/bin/activate"

# Open a bash shell inside the django container.
bash:
    @docker compose exec django bash
