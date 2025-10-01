# SWMM Service v2

Refactored SWMM (Storm Water Management Model) service extracted from `main_old.py` with improved architecture and maintainability.

## Features

- **Water Level Forecasting**: Predict water levels for all nodes in the SWMM model
- **Flood Risk Assessment**: Calculate flood risk based on water levels and ground elevation
- **Node Management**: Get detailed information about all nodes in the model
- **Custom Simulations**: Run custom simulations with user-defined data
- **RESTful API**: Clean, well-documented API endpoints

## Architecture

```
swmm-service-v2/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config/                 # Configuration settings
│   ├── models/                 # Pydantic data models
│   ├── services/               # Business logic services
│   ├── utils/                  # Utility functions
│   └── api/                    # API endpoints
│       └── v1/                 # API version 1
├── tests/                      # Test files
├── model.inp                   # SWMM model file
└── requirements.txt            # Python dependencies
```

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure `model.inp` file is present in the root directory

3. Run the service:

```bash
python -m app.main
```

## API Endpoints

### Health Check

- `GET /health` - Service health status

### SWMM Simulation

- `POST /swmm-api/run-swmm` - Run basic SWMM simulation
- `POST /swmm-api/run-simulation` - Run custom simulation
- `GET /swmm-api/available-nodes` - Get all available nodes

### Forecasting

- `POST /forecast-water-levels` - Forecast water levels for all nodes
- `GET /forecast-water-level/{node_id}` - Forecast for specific node
- `GET /water-level-forecast` - Get water level forecast with caching

### Node Information

- `GET /node-info/{node_id}` - Get detailed node information
- `GET /flood-risk-summary` - Get flood risk summary for all nodes

## Configuration

All configuration is managed in `app/config/settings.py`:

- **API Settings**: Title, version, description
- **CORS Settings**: Allowed origins for cross-origin requests
- **File Paths**: INP file locations and cache paths
- **Simulation Settings**: Default time steps and parameters
- **Flood Risk Settings**: Risk thresholds and levels

## Key Differences from main_old.py

1. **Modular Architecture**: Code is split into logical modules (services, models, utils)
2. **Type Safety**: Uses Pydantic models for data validation
3. **Error Handling**: Improved error handling and logging
4. **Caching**: Built-in caching for simulation results
5. **Documentation**: Comprehensive API documentation
6. **Testing**: Structured test organization

## Development

The service is built using:

- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and settings management
- **PySWMM**: Python wrapper for SWMM
- **Pandas**: Data manipulation and analysis

## License

This project is part of the Hydrology Dashboard system.
