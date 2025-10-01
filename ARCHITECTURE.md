# SWMM Service Architecture

## Overview

This document describes the refactored architecture of the SWMM service, following clean architecture principles for better maintainability, testability, and scalability.

## Directory Structure

```
swmm-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Main application entry point
│   ├── main_old.py            # Backup of original main.py
│   ├── config/                # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py        # Application settings
│   ├── schemas/               # Pydantic models for validation
│   │   ├── __init__.py
│   │   ├── timeseries.py      # Timeseries input/output schemas
│   │   ├── forecast.py        # Forecast-related schemas
│   │   └── response.py        # API response schemas
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── timeseries_utils.py    # Timeseries processing utilities
│   │   ├── flood_risk_utils.py    # Flood risk calculation utilities
│   │   ├── file_utils.py          # File operations utilities
│   │   └── node_utils.py          # Node processing utilities
│   ├── services/              # Business logic layer
│   │   ├── __init__.py
│   │   ├── timeseries_service.py  # Timeseries business logic
│   │   ├── swmm_service.py        # SWMM simulation logic
│   │   ├── forecast_service.py    # Forecast business logic
│   │   └── node_service.py        # Node management logic
│   ├── controllers/           # API controllers
│   │   ├── __init__.py
│   │   ├── swmm_controller.py     # SWMM simulation controller
│   │   ├── forecast_controller.py # Forecast controller
│   │   ├── node_controller.py     # Node controller
│   │   └── health_controller.py   # Health check controller
│   ├── routes/                # API routes
│   │   ├── __init__.py
│   │   ├── swmm_routes.py         # SWMM simulation routes
│   │   ├── forecast_routes.py     # Forecast routes
│   │   ├── node_routes.py         # Node routes
│   │   └── health_routes.py       # Health check routes
│   └── core/                  # Core functionality (future use)
│       └── __init__.py
├── model.inp                  # SWMM model file
├── temp_model.inp            # Temporary model file
└── requirements.txt          # Python dependencies
```

## Architecture Layers

### 1. Schemas Layer (`app/schemas/`)

- **Purpose**: Data validation and serialization
- **Responsibility**: Define Pydantic models for request/response validation
- **Files**:
  - `timeseries.py`: Timeseries input/output schemas
  - `forecast.py`: Forecast-related schemas
  - `response.py`: API response schemas

### 2. Utils Layer (`app/utils/`)

- **Purpose**: Reusable utility functions
- **Responsibility**: Provide common functionality across the application
- **Files**:
  - `timeseries_utils.py`: Timeseries processing utilities
  - `flood_risk_utils.py`: Flood risk calculation utilities
  - `file_utils.py`: File operations utilities
  - `node_utils.py`: Node processing utilities

### 3. Services Layer (`app/services/`)

- **Purpose**: Business logic implementation
- **Responsibility**: Implement core business rules and operations
- **Files**:
  - `timeseries_service.py`: Timeseries business logic
  - `swmm_service.py`: SWMM simulation logic
  - `forecast_service.py`: Forecast business logic
  - `node_service.py`: Node management logic

### 4. Controllers Layer (`app/controllers/`)

- **Purpose**: API request handling
- **Responsibility**: Handle HTTP requests and coordinate with services
- **Files**:
  - `swmm_controller.py`: SWMM simulation controller
  - `forecast_controller.py`: Forecast controller
  - `node_controller.py`: Node controller
  - `health_controller.py`: Health check controller

### 5. Routes Layer (`app/routes/`)

- **Purpose**: API endpoint definitions
- **Responsibility**: Define FastAPI routes and connect to controllers
- **Files**:
  - `swmm_routes.py`: SWMM simulation routes
  - `forecast_routes.py`: Forecast routes
  - `node_routes.py`: Node routes
  - `health_routes.py`: Health check routes

### 6. Configuration Layer (`app/config/`)

- **Purpose**: Application configuration
- **Responsibility**: Manage application settings and configuration
- **Files**:
  - `settings.py`: Application settings

## Key Benefits

### 1. Separation of Concerns

- Each layer has a single responsibility
- Business logic is separated from API handling
- Utilities are reusable across the application

### 2. Maintainability

- Code is organized in logical modules
- Easy to locate and modify specific functionality
- Clear dependencies between layers

### 3. Testability

- Each layer can be tested independently
- Services can be mocked for controller testing
- Utilities can be unit tested in isolation

### 4. Scalability

- Easy to add new features without affecting existing code
- Services can be extended or replaced independently
- Clear interfaces between layers

### 5. Code Reusability

- Utilities can be reused across different services
- Services can be reused across different controllers
- Common functionality is centralized

## Dependencies Flow

```
Routes → Controllers → Services → Utils
   ↓         ↓          ↓        ↓
Schemas ← Response ← Business ← Data
```

## Migration from Original Code

The original `main.py` file (1251 lines) has been refactored into:

1. **Schemas**: 3 files (~150 lines total)
2. **Utils**: 4 files (~400 lines total)
3. **Services**: 4 files (~500 lines total)
4. **Controllers**: 4 files (~300 lines total)
5. **Routes**: 4 files (~100 lines total)
6. **Config**: 1 file (~80 lines total)
7. **Main**: 1 file (~50 lines total)

**Total**: ~1580 lines across 21 files (vs 1251 lines in 1 file)

## Usage

### Running the Application

```bash
# Development
python -m app.main

# Production
uvicorn app.main:app --host 0.0.0.0 --port 1433
```

### API Endpoints

All endpoints are prefixed with `/swmm-api`:

- **SWMM Simulation**:
  - `POST /swmm-api/run-swmm`
  - `POST /swmm-api/run-simulation`

- **Water Level Forecast**:
  - `POST /swmm-api/forecast-water-levels`
  - `GET /swmm-api/forecast-water-level/{node_id}`
  - `GET /swmm-api/water-level-forecast`

- **Nodes**:
  - `GET /swmm-api/available-nodes`
  - `GET /swmm-api/node-info/{node_id}`
  - `GET /swmm-api/flood-risk-summary`

- **Health**:
  - `GET /swmm-api/health`

## Future Enhancements

1. **Database Integration**: Add database layer for persistent storage
2. **Caching**: Implement Redis caching for simulation results
3. **Authentication**: Add JWT authentication
4. **Monitoring**: Add application monitoring and metrics
5. **Testing**: Add comprehensive unit and integration tests
6. **Documentation**: Add OpenAPI documentation
7. **Error Handling**: Implement global error handling middleware
