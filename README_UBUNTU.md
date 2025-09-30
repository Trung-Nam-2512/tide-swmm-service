# SWMM Service - Ubuntu Deployment Guide

## Cài đặt trên Ubuntu

### 1. Cài đặt Python và pip

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Tạo virtual environment

```bash
cd swmm-service
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 4. Chạy service

```bash
cd app
python main.py
```

Service sẽ chạy tại: <http://localhost:8000>

## API Endpoints

- `GET /health` - Health check
- `GET /available-nodes` - Danh sách nodes
- `GET /node-info/{node_id}` - Thông tin chi tiết node
- `POST /run-swmm` - Chạy simulation
- `POST /forecast-water-levels` - Dự báo mực nước
- `GET /forecast-water-level/{node_id}` - Dự báo cho node cụ thể
- `GET /flood-risk-summary` - Tóm tắt rủi ro lũ

## Files quan trọng

- `app/main.py` - Main application
- `model.inp` - SWMM model file
- `temp_model.inp` - Model với timeseries data
- `requirements.txt` - Python dependencies
