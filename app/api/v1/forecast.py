"""
Forecast API endpoints for SWMM Service v2
Extracted from main_old.py
"""

import logging
import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from ...models.request import ForecastRequest
from ...services.swmm_service import write_inp, run_and_parse_swmm
from ...services.forecast_service import create_water_level_forecast
from ...services.timeseries_service import generate_forecast_scenarios
from ...services.node_service import get_available_nodes
from ...utils.file_utils import cleanup_temp_files
from ...utils.swmm_utils import get_node_detailed_info
from ...utils.math_utils import calculate_flood_risk
from ...config.settings import settings

logger = logging.getLogger(__name__)

# Create router
forecast_router = APIRouter()


@forecast_router.post("/forecast-water-levels")
def forecast_water_levels(request: ForecastRequest):
    """Forecast water levels for all nodes or selected nodes (from main_old.py)"""
    try:
        # Tạo scenarios dự báo
        timeseries = generate_forecast_scenarios(
            request.start_date, 
            request.end_date,
            request.rain_scenario,
            request.inflow_scenario,
            request.tide_scenario
        )
        
        # Chạy simulation
        full_inp = write_inp(timeseries)
        simulation_results = run_and_parse_swmm()
        
        # Lọc nodes nếu có filter
        if request.nodes_filter:
            simulation_results = [r for r in simulation_results if r["node"] in request.nodes_filter]
        
        # Tạo dự báo cho từng node
        forecasts = []
        for result in simulation_results:
            forecast = create_water_level_forecast(result["node"], simulation_results)
            forecasts.append(forecast)
        
        return {
            "forecast_period": {
                "start_date": request.start_date,
                "end_date": request.end_date
            },
            "total_nodes": len(forecasts),
            "forecasts": forecasts
        }
        
    except Exception as e:
        logger.error(f"Forecast failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")
    finally:
        import gc
        gc.collect()
        import time
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        cleanup_temp_files(files_to_remove)


@forecast_router.get("/forecast-water-level/{node_id}")
def get_node_forecast(node_id: str, 
                     start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
                     end_date: str = Query(..., description="End date (MM/DD/YYYY)")):
    """Forecast water level for a specific node (from main_old.py)"""
    try:
        # Tạo scenarios dự báo
        timeseries = generate_forecast_scenarios(start_date, end_date)
        
        # Chạy simulation
        full_inp = write_inp(timeseries)
        simulation_results = run_and_parse_swmm()
        
        # Tạo dự báo cho node cụ thể
        forecast = create_water_level_forecast(node_id, simulation_results)
        
        return {
            "node_id": node_id,
            "forecast_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "forecast": forecast
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Node forecast failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Node forecast failed: {str(e)}")
    finally:
        import gc
        gc.collect()
        import time
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        cleanup_temp_files(files_to_remove)


@forecast_router.get("/water-level-forecast")
def get_water_level_forecast(
    start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
    end_date: str = Query(..., description="End date (MM/DD/YYYY)"),
    nodes_filter: Optional[str] = Query(None, description="Comma-separated list of node IDs to filter"),
    use_cached: bool = Query(False, description="Use cached results if available"),
    force_run: bool = Query(False, description="Force run simulation even if cache exists")
):
    """Get water level forecast for all nodes (from main_old.py)"""
    try:
        # Đường dẫn đến file output JSON
        output_json_path = settings.OUTPUT_JSON_FILE
        
        # Kiểm tra xem có file cache không và có sử dụng cache không
        if use_cached and os.path.exists(output_json_path) and not force_run:
            logger.info(f"Using cached SWMM results from {output_json_path}")
            try:
                with open(output_json_path, "r", encoding='utf-8') as f:
                    cached_data = json.load(f)
                    
                # Lọc theo nodes_filter nếu có
                if nodes_filter and "data" in cached_data:
                    selected_nodes = [node.strip() for node in nodes_filter.split(',')]
                    cached_data["data"] = [node for node in cached_data["data"] if node["node_id"] in selected_nodes]
                    cached_data["count"] = len(cached_data["data"])
                    
                return cached_data
            except Exception as e:
                logger.error(f"Error reading cached data: {str(e)}")
                # Tiếp tục chạy mô hình nếu không đọc được cache
        
        # Lấy danh sách nodes
        nodes_response = get_available_nodes()
        if not nodes_response["success"]:
            return {
                "success": False,
                "message": "Failed to get available nodes",
                "data": []
            }
        
        nodes = nodes_response["data"]
        nodes_dict = {node["node_id"]: node for node in nodes}
        
        # Đảm bảo file temp_model.inp tồn tại và có dữ liệu
        inp_file_path = settings.get_temp_inp_file_path()
        if not os.path.exists(inp_file_path) or os.path.getsize(inp_file_path) < 1000:
            # Sao chép từ model.inp nếu cần
            model_inp_path = settings.get_inp_file_path()
            if os.path.exists(model_inp_path):
                logger.info(f"Copying {model_inp_path} to {inp_file_path} for simulation")
                with open(model_inp_path, 'r', encoding='utf-8') as src, open(inp_file_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            else:
                return {
                    "success": False,
                    "message": "Input file for SWMM model not found",
                    "data": []
                }
        
        # Chạy mô hình SWMM và lấy kết quả
        logger.info(f"Running SWMM simulation for {start_date} to {end_date} using {inp_file_path}")
        
        try:
            # Chạy mô hình SWMM với dữ liệu thực từ temp_model.inp
            simulation_results = run_and_parse_swmm()
            
            if not simulation_results:
                return {
                    "success": False,
                    "message": "SWMM simulation returned no results",
                    "data": []
                }
                
            logger.info(f"SWMM simulation completed successfully with {len(simulation_results)} node results")
            
            # Chuyển đổi kết quả từ mô hình sang định dạng forecast
            forecasts = []
            for result in simulation_results:
                node_id = result["node"]
                time_series = result["time_series"]
                
                if not time_series:
                    continue
                
                # Tạo forecast levels từ time series
                forecast_levels = []
                for ts in time_series:
                    # Sử dụng water_level (cao độ mặt nước tuyệt đối) nếu có, nếu không thì tính từ độ sâu và cao độ đáy
                    water_level = ts.get("water_level", None)
                    if water_level is None:
                        invert_elevation = ts.get("invert_elevation", 0)
                        depth = ts.get("depth", 0)
                        water_level = invert_elevation + depth
                    
                    forecast_levels.append({
                        "time": ts["time"],
                        "depth": ts.get("depth", 0),  # Độ sâu nước
                        "water_level": water_level,   # Cao độ mặt nước tuyệt đối
                        "invert_elevation": ts.get("invert_elevation", 0)  # Cao độ đáy
                    })
                
                # Tính toán các thông số
                if forecast_levels:
                    # Lấy thông tin node từ nodes_dict và kết quả mô hình
                    node_info = nodes_dict.get(node_id, {})
                    ground_elevation = node_info.get("ground_elevation", 0)
                    invert_elevation = result.get("invert_elevation", node_info.get("invert_elevation", 0))
                    
                    # Lấy mực nước hiện tại và mực nước cao nhất
                    current_water_level = forecast_levels[-1]["water_level"]
                    max_water_level = result.get("max_water_level_m", max(f["water_level"] for f in forecast_levels))
                    current_depth = forecast_levels[-1]["depth"]
                    max_depth = result.get("max_depth_m", max(f["depth"] for f in forecast_levels))
                    
                    # Tính toán nguy cơ ngập lụt dựa trên mực nước so với cao độ mặt đất
                    # Ngưỡng ngập là khi mực nước vượt quá cao độ mặt đất + 0.3m
                    flood_threshold = 0.3
                    
                    # Tính mức độ ngập so với mặt đất
                    flood_depth = max(0, max_water_level - ground_elevation)
                    
                    # Tính toán nguy cơ ngập
                    if flood_depth <= 0:
                        flood_risk = "NONE"
                        flood_probability = 0.0
                    elif flood_depth < flood_threshold:
                        flood_risk = "LOW"
                        flood_probability = flood_depth / flood_threshold * 0.3  # max 30%
                    elif flood_depth < flood_threshold * 2:
                        flood_risk = "MEDIUM"
                        flood_probability = 0.3 + (flood_depth - flood_threshold) / flood_threshold * 0.3  # 30-60%
                    elif flood_depth < flood_threshold * 3:
                        flood_risk = "HIGH"
                        flood_probability = 0.6 + (flood_depth - flood_threshold * 2) / flood_threshold * 0.25  # 60-85%
                    else:
                        flood_risk = "CRITICAL"
                        flood_probability = min(0.85 + (flood_depth - flood_threshold * 3) / flood_threshold * 0.15, 1.0)  # 85-100%
                    
                    forecast = {
                        "node_id": node_id,
                        "current_water_level": current_water_level,  # Cao độ mặt nước hiện tại (tuyệt đối)
                        "max_water_level": max_water_level,          # Cao độ mặt nước cao nhất (tuyệt đối)
                        "current_depth": current_depth,              # Độ sâu nước hiện tại
                        "max_depth": max_depth,                      # Độ sâu nước lớn nhất
                        "invert_elevation": invert_elevation,        # Cao độ đáy
                        "ground_elevation": ground_elevation,        # Cao độ mặt đất
                        "flood_depth": flood_depth,                  # Độ sâu ngập (so với mặt đất)
                        "flood_risk": flood_risk,                    # Mức độ nguy cơ ngập
                        "flood_probability": flood_probability,      # Xác suất ngập
                        "forecast_levels": forecast_levels           # Chuỗi thời gian dự báo
                    }
                    forecasts.append(forecast)
            
            # Lọc theo nodes_filter nếu có
            if nodes_filter:
                selected_nodes = [node.strip() for node in nodes_filter.split(',')]
                forecasts = [forecast for forecast in forecasts if forecast["node_id"] in selected_nodes]
            
            # Tạo kết quả
            result = {
                "success": True,
                "data": forecasts,
                "count": len(forecasts),
                "simulation_info": {
                    "ìnor": "từ tù",
                    # "inp_file": inp_file_path,
                }
            }
            
            # Lưu kết quả vào file JSON để cache
            try:
                with open(output_json_path, "w", encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Saved SWMM results to {output_json_path}")
            except Exception as e:
                logger.error(f"Error saving SWMM results to JSON: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error running SWMM simulation: {str(e)}")
            return {
                "success": False,
                "message": f"Error running SWMM simulation: {str(e)}",
                "data": []
            }
    except Exception as e:
        logger.error(f"Failed to get water level forecast: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get water level forecast: {str(e)}",
            "data": []
        }
