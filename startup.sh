#!/bin/bash
set -e

APP_DIR=/home/site/wwwroot
cd $APP_DIR

if [ ! -d "antenv" ]; then
  echo "[startup] Creating venv..."
  python -m venv antenv
  source antenv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  source antenv/bin/activate
fi

exec python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0