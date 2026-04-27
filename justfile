start:
    rm -rf logs/
    caffeinate -i uv run main.py

clear:
    rm -rf logs/

docker-restart:
    docker compose down
    caffeinate -s docker compose up --build -d

docker-fresh-restart:
    docker compose down
    rm -rf logs/
    rm -f config/opponents.db
    caffeinate -s docker compose up --build -d
