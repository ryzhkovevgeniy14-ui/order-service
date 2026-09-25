#!/bin/bash

python bin/outbox_worker.py &
python bin/consumer.py &
uvicorn order_service.fastapi:create_app --factory --host 0.0.0.0 --port 8000 &

wait