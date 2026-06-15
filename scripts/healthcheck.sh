#!/bin/bash
# Health check — verifies all core services are responding
curl -sf http://127.0.0.1:8199/system_stats > /dev/null && \
curl -sf http://127.0.0.1:8000/health > /dev/null && \
curl -sf http://127.0.0.1:3000/ > /dev/null
