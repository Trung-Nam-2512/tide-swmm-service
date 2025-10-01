"""
SWMM API endpoints for SWMM Service v2
Extracted from main_old.py
"""

import logging
from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, List, Any, Optional
from ...models.timeseries import TimeseriesInput, SimulationInput
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

# Create router with prefix /swmm-api
swmm_router = APIRouter(prefix="/swmm-api")


@swmm_router.post("/run-swmm")
def run_model(timeseries: TimeseriesInput = Body(...)):
    """Run SWMM simulation with timeseries data (from main_old.py)"""
    try:
        full_inp = write_inp(timeseries)
        results = run_and_parse_swmm()
        return {"results": results}
    finally:
        import gc
        gc.collect()
        import time
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        cleanup_temp_files(files_to_remove)


@swmm_router.post("/run-simulation")
def run_custom_simulation(simulation_input: SimulationInput = Body(...)):
    """
    Run custom simulation with user-defined data (from main_old.py)
    """
    try:
        logger.info(f"Running custom simulation: {simulation_input.simulation_name}")
        
        # Chuyển đổi dữ liệu từ frontend sang format TimeseriesInput
        timeseries_data = TimeseriesInput(
            rain={item["time"]: item["value"] for item in simulation_input.timeseries.get("rainfall", [])},
            inflow_dautieng={item["time"]: item["value"] for item in simulation_input.timeseries.get("dauTieng", [])},
            inflow_trian={item["time"]: item["value"] for item in simulation_input.timeseries.get("triAn", [])},
            tide={item["time"]: item["value"] for item in simulation_input.timeseries.get("tide", [])}
        )
        
        # Tạo file INP với dữ liệu mới
        inp_content = write_inp(timeseries_data)
        
        # Lưu file INP tùy chỉnh
        import os
        custom_inp_path = os.path.join(os.path.dirname(__file__), f"custom_{simulation_input.simulation_name.replace(' ', '_')}.inp")
        with open(custom_inp_path, 'w', encoding='utf-8') as f:
            f.write(inp_content)
        
        logger.info(f"Custom INP file created: {custom_inp_path}")
        
        # Chạy mô hình SWMM với file tùy chỉnh
        from pyswmm import Simulation, Nodes
        with Simulation(custom_inp_path) as sim:
            all_results = []
            nodes = Nodes(sim)
            
            # Tạo dictionary để lưu data cho tất cả nodes
            node_list = list(nodes)
            node_data = {node.nodeid: {"depths": [], "invert_elev": node.invert_elevation} for node in node_list}
            
            logger.info(f"Found {len(node_list)} nodes in the custom model")
            
            # Chạy simulation và thu thập data
            step_count = 0
            last_saved_time = None
            
            # Log thời gian bắt đầu và kết thúc của mô hình
            start_time = sim.start_time
            end_time = sim.end_time
            logger.info(f"Custom simulation period: {start_time} to {end_time}")
            
            # Chạy mô hình từng bước thời gian
            for step in sim:
                step_count += 1
                current_time = sim.current_time
                current_hour = current_time.strftime("%m/%d/%Y %H:00")
                
                # Lưu data mỗi giờ (khi minute = 0) hoặc mỗi 15 phút
                should_save = (current_time.minute == 0) or (current_time.minute % 15 == 0)
                
                if should_save and (last_saved_time is None or current_hour != last_saved_time):
                    for node in node_list:
                        node_id = node.nodeid
                        depth = float(node.depth)
                        inflow = float(getattr(node, 'total_inflow', 0.0))
                        head = float(getattr(node, 'head', node.invert_elevation + depth))
                        invert_elev = float(node.invert_elevation)
                        
                        # Tính mực nước theo cao độ (head = invert_elevation + depth)
                        water_level = head
                        
                        node_data[node_id]["depths"].append({
                            "time": current_hour,
                            "depth": depth,
                            "inflow": inflow,
                            "water_level": water_level,
                            "invert_elevation": invert_elev
                        })
                    
                    last_saved_time = current_hour
                    
                    # Log tiến trình mỗi 24 giờ
                    if step_count % 96 == 0:  # 24 giờ * 4 (15 phút mỗi bước)
                        logger.info(f"Custom simulation progress: {current_time} (step {step_count})")
            
            logger.info(f"Custom simulation completed with {step_count} steps")

            # Tạo kết quả cho mỗi node
            for node_id, data in node_data.items():
                depths = data["depths"]
                invert_elev = data["invert_elev"]
                if depths:
                    max_depth = max(d["depth"] for d in depths)
                    max_water_level = max(d["water_level"] for d in depths)
                    result = {
                        "node": node_id,
                        "max_depth_m": max_depth,
                        "max_water_level_m": max_water_level,
                        "invert_elevation": invert_elev,
                        "time_series": depths
                    }
                    all_results.append(result)

            logger.info(f"Custom simulation completed. Found {len(all_results)} nodes with data")
            
            # Lưu kết quả vào file JSON
            results_file = os.path.join(os.path.dirname(__file__), f"custom_results_{simulation_input.simulation_name.replace(' ', '_')}.json")
            import json
            from datetime import datetime
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "simulation_name": simulation_input.simulation_name,
                    "start_date": simulation_input.start_date,
                    "end_date": simulation_input.end_date,
                    "time_step": simulation_input.time_step,
                    "results": all_results,
                    "created_at": datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"Custom simulation results saved to: {results_file}")
            
            return {
                "success": True,
                "simulation_name": simulation_input.simulation_name,
                "results": all_results,
                "total_nodes": len(all_results),
                "results_file": results_file
            }
            
    except Exception as e:
        logger.error(f"Error running custom simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running custom simulation: {str(e)}")


@swmm_router.get("/available-nodes")
def get_available_nodes_endpoint():
    """Get list of all available nodes with coordinates (from main_old.py)"""
    return get_available_nodes()
