#!/bin/bash

uv run python bin/outbox_worker.py &
uv run python bin/consumer.py &
uv run uvicorn order_service.fastapi:create_app --factory --host 0.0.0.0 --port 8000 &

wait