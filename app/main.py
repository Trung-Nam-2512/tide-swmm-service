from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import pandas as pd
import json
import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pyswmm import Simulation, Nodes
import numpy as np
import time
import re
import logging
import random


app = FastAPI()

# Tạo router với prefix /swmm-api
from fastapi import APIRouter
swmm_router = APIRouter(prefix="/swmm-api")

# Cấu hình CORS để cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend development
        "https://tide.nguyentrungnam.com",  # Frontend production
        "https://www.tide.nguyentrungnam.com",
        "http://wlforecast.baonamdts.com/",  # Frontend production with www
        "*"  # Fallback for development
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả HTTP methods
    allow_headers=["*"],  # Cho phép tất cả headers
)

# Thêm router vào app
app.include_router(swmm_router)

# Root endpoint
@app.get("/")
def root():
    return {"message": "SWMM Water Level Forecast API", "version": "1.0.0", "docs": "/docs"}

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Đường dẫn đến file .inp gốc
INP_FILE = os.path.join(os.path.dirname(__file__), "..", "model.inp")

if not os.path.exists(INP_FILE):
    raise Exception("model.inp not found. Please ensure it exists in the project directory.")

class TimeseriesInput(BaseModel):
    rain: Dict[str, float]  # "MM/DD/YYYY HH:MM" -> mm/hr
    inflow_dautieng: Dict[str, float]  # m3/s
    inflow_trian: Dict[str, float]  # m3/s
    tide: Dict[str, float]  # m

class SimulationInput(BaseModel):
    simulation_name: str
    start_date: str
    end_date: str
    time_step: int
    timeseries: Dict[str, List[Dict[str, Any]]]

class ForecastLevel(BaseModel):
    time: str  # "MM/DD/YYYY HH:MM"
    level: float  # m

class NodeInfo(BaseModel):
    node_id: str
    node_type: str  # "JUNCTION", "STORAGE", "OUTFALL"
    x_coordinate: float
    y_coordinate: float
    invert_elevation: float  # m
    ground_elevation: float  # m
    max_depth: float  # m
    initial_depth: float  # m
    surface_depth: float  # m
    ponded_area: float  # m²

class WaterLevelForecast(BaseModel):
    node_id: str
    node_info: NodeInfo
    current_level: float  # m
    forecast_levels: List[ForecastLevel]  # List of time-level pairs
    max_forecast_level: float  # m
    flood_risk: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    flood_probability: float  # 0.0 - 1.0

class ForecastRequest(BaseModel):
    start_date: str  # "MM/DD/YYYY"
    end_date: str    # "MM/DD/YYYY"
    rain_scenario: Optional[Dict[str, float]] = None  # Custom rain data
    inflow_scenario: Optional[Dict[str, float]] = None  # Custom inflow data
    tide_scenario: Optional[Dict[str, float]] = None  # Custom tide data
    nodes_filter: Optional[List[str]] = None  # Specific nodes to forecast

def interpolate_ts(ts_dict):
    if not ts_dict:
        return {}
    times = sorted([datetime.strptime(t, "%m/%d/%Y %H:%M") for t in ts_dict.keys()])
    values = [ts_dict[times[i].strftime("%m/%d/%Y %H:%M")] for i in range(len(times))]
    full_times = pd.date_range(times[0], times[-1], freq="H")
    interp_values = np.interp([t.timestamp() for t in full_times], [t.timestamp() for t in times], values)
    return {full_times[i].strftime("%m/%d/%Y %H:%M"): interp_values[i] for i in range(len(full_times))}

def generate_forecast_scenarios(start_date: str, end_date: str, 
                               rain_scenario: Optional[Dict[str, float]] = None,
                               inflow_scenario: Optional[Dict[str, float]] = None,
                               tide_scenario: Optional[Dict[str, float]] = None) -> TimeseriesInput:
    """Tạo scenarios dự báo dựa trên input hoặc dữ liệu mặc định"""
    
    # Tạo date range
    start_dt = datetime.strptime(start_date, "%m/%d/%Y")
    end_dt = datetime.strptime(end_date, "%m/%d/%Y")
    date_range = pd.date_range(start_dt, end_dt, freq="H")
    
    # Tạo rain scenario
    if rain_scenario:
        rain_data = interpolate_ts(rain_scenario)
    else:
        # Dự báo mưa dựa trên pattern lịch sử
        rain_data = {dt.strftime("%m/%d/%Y %H:%M"): 
                    max(0, 3 * np.sin(2 * np.pi * i / 24) + 2 + np.random.normal(0, 1)) 
                    for i, dt in enumerate(date_range)}
    
    # Tạo inflow scenario
    if inflow_scenario:
        inflow_dt_data = interpolate_ts(inflow_scenario)
        inflow_ta_data = interpolate_ts(inflow_scenario)
    else:
        # Dự báo lưu lượng ổn định
        inflow_dt_data = {dt.strftime("%m/%d/%Y %H:%M"): 24.0 for dt in date_range}
        inflow_ta_data = {dt.strftime("%m/%d/%Y %H:%M"): 800.0 for dt in date_range}
    
    # Tạo tide scenario
    if tide_scenario:
        tide_data = interpolate_ts(tide_scenario)
    else:
        # Dự báo thủy triều dựa trên chu kỳ
        tide_data = {dt.strftime("%m/%d/%Y %H:%M"): 
                    1.5 * np.sin(2 * np.pi * i / 12.4) + 1.0 + np.random.normal(0, 0.1)
                    for i, dt in enumerate(date_range)}
    
    return TimeseriesInput(
        rain=rain_data,
        inflow_dautieng=inflow_dt_data,
        inflow_trian=inflow_ta_data,
        tide=tide_data
    )

def calculate_flood_risk(max_depth: float, invert_elevation: float = 0.0, 
                        ground_elevation: float = 0.0, node_capacity: float = 25.0) -> tuple:
    """Tính toán nguy cơ ngập lụt dựa trên mực nước thực tế"""
    
    # Tính mực nước thực tế (water level = depth + invert elevation)
    water_level = max_depth + invert_elevation
    
    # Tính tỷ lệ ngập lụt
    if ground_elevation > invert_elevation and (ground_elevation - invert_elevation) > 0:
        # Sử dụng cao độ thực tế
        flood_ratio = max_depth / (ground_elevation - invert_elevation)
    elif node_capacity > 0:
        # Fallback to node capacity
        flood_ratio = max_depth / node_capacity
    else:
        # Fallback to max_depth if all else fails
        flood_ratio = min(max_depth / 25.0, 1.0)  # Assume 25m as default capacity
    
    # Đảm bảo flood_ratio trong khoảng hợp lý
    flood_ratio = max(0.0, min(flood_ratio, 2.0))  # Cap at 200%
    
    # Đánh giá nguy cơ dựa trên tỷ lệ ngập lụt
    if flood_ratio <= 0.3:
        return "LOW", 0.1
    elif flood_ratio <= 0.6:
        return "MEDIUM", 0.3
    elif flood_ratio <= 0.85:
        return "HIGH", 0.7
    else:
        return "CRITICAL", 0.9

def get_node_detailed_info(node_id: str) -> NodeInfo:
    """Lấy thông tin chi tiết của node từ model.inp"""
    try:
        # Đọc file model.inp để lấy thông tin chi tiết
        with open(INP_FILE, "r") as f:
            content = f.read()
        
        # Xác định loại node
        node_type = "JUNCTION"
        if "SG" in node_id:
            node_type = "STORAGE"
        elif "OUT" in node_id or "OUTFALL" in node_id:
            node_type = "OUTFALL"
        
        # Tìm tọa độ trong [COORDINATES]
        coords_pattern = r'\[COORDINATES\](.*?)(?=\[|\Z)'
        coords_match = re.search(coords_pattern, content, re.DOTALL)
        x_coord, y_coord = 0.0, 0.0
        
        if coords_match:
            coords_content = coords_match.group(1)
            coord_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)'
            coord_match = re.search(coord_pattern, coords_content, re.MULTILINE)
            if coord_match:
                x_coord = float(coord_match.group(1))
                y_coord = float(coord_match.group(2))
        
        # Tìm thông tin cao độ và dung tích
        invert_elevation, max_depth, initial_depth, surface_depth, ponded_area = 0.0, 0.0, 0.0, 0.0, 0.0
        
        if node_type == "JUNCTION":
            section_pattern = r'\[JUNCTIONS\](.*?)(?=\[|\Z)'
            section_match = re.search(section_pattern, content, re.DOTALL)
            if section_match:
                section_content = section_match.group(1)
                # Format: Name Elevation MaxDepth InitDepth SurDepth Aponded
                node_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                node_match = re.search(node_pattern, section_content, re.MULTILINE)
                if node_match:
                    invert_elevation = float(node_match.group(1))
                    max_depth = float(node_match.group(2))
                    initial_depth = float(node_match.group(3))
                    surface_depth = float(node_match.group(4))
                    ponded_area = float(node_match.group(5))
        
        elif node_type == "STORAGE":
            section_pattern = r'\[STORAGE\](.*?)(?=\[|\Z)'
            section_match = re.search(section_pattern, content, re.DOTALL)
            if section_match:
                section_content = section_match.group(1)
                # Format: Name Elevation MaxDepth InitDepth SurDepth Aponded
                node_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                node_match = re.search(node_pattern, section_content, re.MULTILINE)
                if node_match:
                    invert_elevation = float(node_match.group(1))
                    max_depth = float(node_match.group(2))
                    initial_depth = float(node_match.group(3))
                    surface_depth = float(node_match.group(4))
                    ponded_area = float(node_match.group(5))
        
        # Tính cao độ mặt đất (ground elevation = invert + max_depth)
        ground_elevation = invert_elevation + max_depth
        
        return NodeInfo(
            node_id=node_id,
            node_type=node_type,
            x_coordinate=x_coord,
            y_coordinate=y_coord,
            invert_elevation=invert_elevation,
            ground_elevation=ground_elevation,
            max_depth=max_depth,
            initial_depth=initial_depth,
            surface_depth=surface_depth,
            ponded_area=ponded_area
        )
        
    except Exception as e:
        logger.warning(f"Could not read detailed info for {node_id}: {str(e)}")
        # Fallback to default values
        if "DN" in node_id:
            return NodeInfo(
                node_id=node_id,
                node_type="JUNCTION",
                x_coordinate=0.0,
                y_coordinate=0.0,
                invert_elevation=0.0,
                ground_elevation=2.0,
                max_depth=20.0,
                initial_depth=0.0,
                surface_depth=0.0,
                ponded_area=0.0
            )
        elif "SG" in node_id:
            return NodeInfo(
                node_id=node_id,
                node_type="STORAGE",
                x_coordinate=0.0,
                y_coordinate=0.0,
                invert_elevation=0.0,
                ground_elevation=3.0,
                max_depth=30.0,
                initial_depth=0.0,
                surface_depth=0.0,
                ponded_area=0.0
            )
        else:
            return NodeInfo(
                node_id=node_id,
                node_type="JUNCTION",
                x_coordinate=0.0,
                y_coordinate=0.0,
                invert_elevation=0.0,
                ground_elevation=2.5,
                max_depth=25.0,
                initial_depth=0.0,
                surface_depth=0.0,
                ponded_area=0.0
            )

def get_node_elevation_data(node_id: str) -> tuple:
    """Lấy thông tin cao độ của node từ model.inp (backward compatibility)"""
    node_info = get_node_detailed_info(node_id)
    return node_info.invert_elevation, node_info.ground_elevation, node_info.max_depth

def create_water_level_forecast(node_id: str, simulation_results: List[Dict], 
                               current_time: str = None) -> WaterLevelForecast:
    """Tạo dự báo mực nước cho một node cụ thể"""
    
    # Tìm node trong kết quả simulation
    node_data = None
    for result in simulation_results:
        if result["node"] == node_id:
            node_data = result
            break
    
    if not node_data:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in simulation results")
    
    time_series = node_data["time_series"]
    if not time_series:
        raise HTTPException(status_code=400, detail=f"No time series data for node {node_id}")
    
    # Lấy thông tin chi tiết của node
    node_info = get_node_detailed_info(node_id)
    
    # Lấy mực nước hiện tại (giờ cuối cùng)
    current_depth = time_series[-1]["depth"] if time_series else 0.0
    current_level = current_depth + node_info.invert_elevation  # Water level = depth + invert elevation
    
    # Tạo forecast levels (chuyển đổi depth thành water level)
    forecast_levels = []
    for ts in time_series:
        water_level = ts["depth"] + node_info.invert_elevation
        forecast_levels.append(ForecastLevel(
            time=ts["time"],
            level=water_level  # Mực nước thực tế
        ))
    
    max_depth = node_data["max_depth_m"]
    max_forecast_level = max_depth + node_info.invert_elevation  # Mực nước tối đa thực tế
    
    # Tính nguy cơ ngập lụt với thông tin địa hình
    flood_risk, flood_probability = calculate_flood_risk(
        max_depth, node_info.invert_elevation, node_info.ground_elevation, node_info.max_depth
    )
    
    return WaterLevelForecast(
        node_id=node_id,
        node_info=node_info,
        current_level=current_level,
        forecast_levels=forecast_levels,
        max_forecast_level=max_forecast_level,
        flood_risk=flood_risk,
        flood_probability=flood_probability
    )

def write_inp(timeseries: TimeseriesInput):
    with open(INP_FILE, "r") as f:
        base_inp = f.read()

    # Interpolate tất cả timeseries
    timeseries.rain = interpolate_ts(timeseries.rain)
    timeseries.inflow_dautieng = interpolate_ts(timeseries.inflow_dautieng)
    timeseries.inflow_trian = interpolate_ts(timeseries.inflow_trian)
    timeseries.tide = interpolate_ts(timeseries.tide)

    # Format TIMESERIES
    tsn = "\n".join([f"TSN   {dt}   {val}" for dt, val in timeseries.rain.items()])
    inflow_dt = "\n".join([f"Inflow_DauTieng   {dt}   {val}" for dt, val in timeseries.inflow_dautieng.items()])
    inflow_ta = "\n".join([f"Inflow_TriAn   {dt}   {val}" for dt, val in timeseries.inflow_trian.items()])
    vt = "\n".join([f"VT   {dt}   {val}" for dt, val in timeseries.tide.items()])

    inflows_section = f"""[INFLOWS]
;;Node           Constituent      Time Series      Type    Mfactor  Sfactor
0SG              FLOW             Inflow_DauTieng  FLOW    1.0      1.0
0DN              FLOW             Inflow_TriAn     FLOW    1.0      1.0
"""

    timeseries_section = f"""[TIMESERIES]
{tsn}
{inflow_dt}
{inflow_ta}
{vt}
"""

    # Xóa sections cũ trước
    base_inp = re.sub(r'\[TIMESERIES\].*?(?=\[|$)', '', base_inp, flags=re.DOTALL)
    base_inp = re.sub(r'\[INFLOWS\].*?(?=\[|$)', '', base_inp, flags=re.DOTALL)
    
    # Thêm sections mới ở cuối file
    base_inp = base_inp.rstrip() + "\n\n" + inflows_section + timeseries_section

    full_inp = base_inp

    with open("temp_model.inp", "w") as f:
        f.write(full_inp)

    return full_inp

def run_and_parse_swmm():
    """
    Chạy mô hình SWMM và phân tích kết quả
    Sử dụng giải pháp đơn giản hơn để tránh lỗi subprocess
    """
    try:
        # Đảm bảo đường dẫn tới file temp_model.inp là chính xác
        inp_file_path = os.path.join(os.path.dirname(__file__), "temp_model.inp")
        
        # Kiểm tra xem file có tồn tại không
        if not os.path.exists(inp_file_path):
            # Nếu không tồn tại, sao chép từ model.inp
            model_inp_path = os.path.join(os.path.dirname(__file__), "..", "model.inp")
            if os.path.exists(model_inp_path):
                logger.info(f"Copying {model_inp_path} to {inp_file_path}")
                with open(model_inp_path, 'r') as src, open(inp_file_path, 'w') as dst:
                    dst.write(src.read())
            else:
                raise Exception(f"Neither temp_model.inp nor model.inp found at {os.path.dirname(__file__)}")
        
        # Log thông tin file trước khi chạy
        file_size = os.path.getsize(inp_file_path)
        logger.info(f"Running SWMM simulation with {inp_file_path} (size: {file_size} bytes)...")
        
        # Kiểm tra xem có file cache không
        cache_file = os.path.join(os.path.dirname(__file__), "swmm_simulation_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    all_results = json.load(f)
                    logger.info(f"Loaded simulation results from cache: {len(all_results)} nodes")
                    return all_results
            except Exception as e:
                logger.error(f"Failed to load simulation cache: {str(e)}")
        
        
        # Thử chạy mô hình SWMM trực tiếp (không dùng subprocess)
        logger.info(f"Attempting to run SWMM simulation directly...")
        try:
            # Chạy mô hình SWMM trực tiếp
            with Simulation(inp_file_path) as sim:
                all_results = []
                nodes = Nodes(sim)
                
                # Tạo dictionary để lưu data cho tất cả nodes
                node_list = list(nodes)
                node_data = {node.nodeid: {"depths": [], "invert_elev": node.invert_elevation} for node in node_list}
                
                logger.info(f"Found {len(node_list)} nodes in the model")
                
                # Chạy simulation và thu thập data
                step_count = 0
                last_saved_time = None
                
                # Log thời gian bắt đầu và kết thúc của mô hình
                start_time = sim.start_time
                end_time = sim.end_time
                logger.info(f"Simulation period: {start_time} to {end_time}")
                
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
                            # head là cao độ mặt nước tuyệt đối, depth là độ sâu nước
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
                            logger.info(f"Simulation progress: {current_time} (step {step_count})")
                
                logger.info(f"Simulation completed with {step_count} steps")

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

                logger.info(f"Simulation completed. Found {len(all_results)} nodes with data")
                
                # Lưu kết quả vào cache
                with open(cache_file, 'w') as f:
                    json.dump(all_results, f, indent=2)
                
                # Lưu kết quả vào file debug
                debug_output_path = os.path.join(os.path.dirname(__file__), "swmm_debug_output.json")
                try:
                    with open(debug_output_path, "w") as f:
                        json.dump(all_results, f, indent=2)
                    logger.info(f"Saved debug output to {debug_output_path}")
                except Exception as e:
                    logger.error(f"Failed to save debug output: {str(e)}")
                
                return all_results
                
        except Exception as e:
            logger.error(f"Direct SWMM simulation failed: {str(e)}")
            raise Exception(f"SWMM simulation failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"SWMM simulation or parsing failed: {str(e)}")
        raise Exception(f"SWMM simulation failed: {str(e)}")

@swmm_router.post("/run-swmm")
def run_model(timeseries: TimeseriesInput = Body(...)):
    try:
        full_inp = write_inp(timeseries)
        results = run_and_parse_swmm()
        return {"results": results}
    finally:
        import gc
        gc.collect()
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                for attempt in range(3):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                            gc.collect()
                        else:
                            logger.warning(f"Could not delete {file_path} - file may be in use")

@swmm_router.post("/run-simulation")
def run_custom_simulation(simulation_input: SimulationInput = Body(...)):
    """
    Chạy mô hình SWMM với dữ liệu đầu vào tùy chỉnh từ frontend
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
        custom_inp_path = os.path.join(os.path.dirname(__file__), f"custom_{simulation_input.simulation_name.replace(' ', '_')}.inp")
        with open(custom_inp_path, 'w') as f:
            f.write(inp_content)
        
        logger.info(f"Custom INP file created: {custom_inp_path}")
        
        # Chạy mô hình SWMM với file tùy chỉnh
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
            with open(results_file, 'w') as f:
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

@swmm_router.post("/forecast-water-levels")
def forecast_water_levels(request: ForecastRequest):
    """Dự báo mực nước cho tất cả nodes hoặc nodes được chọn"""
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
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                for attempt in range(3):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                            gc.collect()
                        else:
                            logger.warning(f"Could not delete {file_path} - file may be in use")

@swmm_router.get("/forecast-water-level/{node_id}")
def get_node_forecast(node_id: str, 
                     start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
                     end_date: str = Query(..., description="End date (MM/DD/YYYY)")):
    """Dự báo mực nước cho một node cụ thể"""
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
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                for attempt in range(3):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                            gc.collect()
                        else:
                            logger.warning(f"Could not delete {file_path} - file may be in use")

@swmm_router.get("/node-info/{node_id}")
def get_node_info(node_id: str):
    """Lấy thông tin chi tiết của một node"""
    try:
        node_info = get_node_detailed_info(node_id)
        return {
            "node_id": node_info.node_id,
            "node_type": node_info.node_type,
            "coordinates": {
                "x": node_info.x_coordinate,
                "y": node_info.y_coordinate
            },
            "elevation": {
                "invert_elevation": node_info.invert_elevation,
                "ground_elevation": node_info.ground_elevation,
                "max_depth": node_info.max_depth
            },
            "initial_conditions": {
                "initial_depth": node_info.initial_depth,
                "surface_depth": node_info.surface_depth,
                "ponded_area": node_info.ponded_area
            }
        }
    except Exception as e:
        logger.error(f"Failed to get node info for {node_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get node info: {str(e)}")

@swmm_router.get("/flood-risk-summary")
def get_flood_risk_summary(start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
                          end_date: str = Query(..., description="End date (MM/DD/YYYY)")):
    """Tóm tắt nguy cơ ngập lụt cho tất cả nodes"""
    try:
        # Tạo scenarios dự báo
        timeseries = generate_forecast_scenarios(start_date, end_date)
        
        # Chạy simulation
        full_inp = write_inp(timeseries)
        simulation_results = run_and_parse_swmm()
        
        # Phân loại nodes theo nguy cơ ngập lụt
        risk_categories = {
            "LOW": [],
            "MEDIUM": [],
            "HIGH": [],
            "CRITICAL": []
        }
        
        for result in simulation_results:
            # Lấy thông tin chi tiết của node
            node_info = get_node_detailed_info(result["node"])
            
            # Tính nguy cơ ngập lụt với thông tin địa hình
            flood_risk, flood_probability = calculate_flood_risk(
                result["max_depth_m"], node_info.invert_elevation, node_info.ground_elevation, node_info.max_depth
            )
            
            risk_categories[flood_risk].append({
                "node_id": result["node"],
                "node_type": node_info.node_type,
                "coordinates": {
                    "x": node_info.x_coordinate,
                    "y": node_info.y_coordinate
                },
                "max_depth": result["max_depth_m"],
                "max_water_level": result["max_depth_m"] + node_info.invert_elevation,
                "flood_probability": flood_probability,
                "invert_elevation": node_info.invert_elevation,
                "ground_elevation": node_info.ground_elevation
            })
        
        # Tính tổng kết
        total_nodes = len(simulation_results)
        summary = {
            "forecast_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_nodes": total_nodes,
            "risk_distribution": {
                "LOW": len(risk_categories["LOW"]),
                "MEDIUM": len(risk_categories["MEDIUM"]),
                "HIGH": len(risk_categories["HIGH"]),
                "CRITICAL": len(risk_categories["CRITICAL"])
            },
            "risk_categories": risk_categories
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Flood risk summary failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flood risk summary failed: {str(e)}")
    finally:
        import gc
        gc.collect()
        time.sleep(2)
        files_to_remove = ["temp_model.inp", "temp_model.rpt", "temp_model.out"]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                for attempt in range(3):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                            gc.collect()
                        else:
                            logger.warning(f"Could not delete {file_path} - file may be in use")

# Default timeseries
date_range = pd.date_range("2025-09-29 00:00", "2025-10-05 23:00", freq="H")
DEFAULT_TIMESERIES = TimeseriesInput(
    rain={dt.strftime("%m/%d/%Y %H:%M"): max(0, 5 * np.sin(2 * np.pi * i / 24) + 5) for i, dt in enumerate(date_range)},
    inflow_dautieng={dt.strftime("%m/%d/%Y %H:%M"): 24.0 for dt in date_range},
    inflow_trian={dt.strftime("%m/%d/%Y %H:%M"): 800.0 for dt in date_range},
    tide={dt.strftime("%m/%d/%Y %H:%M"): 1.5 * np.sin(2 * np.pi * i / 12.4) + 1.0 for i, dt in enumerate(date_range)}
)

@swmm_router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SWMM Water Level Forecast API", "version": "1.0.0"}

@swmm_router.get("/water-level-forecast")
def get_water_level_forecast(
    start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
    end_date: str = Query(..., description="End date (MM/DD/YYYY)"),
    nodes_filter: Optional[str] = Query(None, description="Comma-separated list of node IDs to filter"),
    use_cached: bool = Query(False, description="Use cached results if available"),
    force_run: bool = Query(False, description="Force run simulation even if cache exists")
):
    """Lấy dự báo mực nước cho tất cả nodes bằng cách chạy mô hình SWMM với dữ liệu thực từ temp_model.inp"""
    try:
        # Đường dẫn đến file output JSON
        output_json_path = os.path.join(os.path.dirname(__file__), "swmm_output.json")
        
        # Kiểm tra xem có file cache không và có sử dụng cache không
        if use_cached and os.path.exists(output_json_path) and not force_run:
            logger.info(f"Using cached SWMM results from {output_json_path}")
            try:
                with open(output_json_path, "r") as f:
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
        inp_file_path = os.path.join(os.path.dirname(__file__), "temp_model.inp")
        if not os.path.exists(inp_file_path) or os.path.getsize(inp_file_path) < 1000:
            # Sao chép từ model.inp nếu cần
            model_inp_path = os.path.join(os.path.dirname(__file__), "..", "model.inp")
            if os.path.exists(model_inp_path):
                logger.info(f"Copying {model_inp_path} to {inp_file_path} for simulation")
                with open(model_inp_path, 'r') as src, open(inp_file_path, 'w') as dst:
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
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_nodes": len(forecasts),
                    "simulation_time": datetime.now().isoformat(),
                    "inp_file": inp_file_path,
                    "model_type": "SWMM Real Simulation"
                }
            }
            
            # Lưu kết quả vào file JSON để cache
            try:
                with open(output_json_path, "w") as f:
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

@swmm_router.get("/available-nodes")
def get_available_nodes():
    """Lấy danh sách tất cả nodes có sẵn với tọa độ"""
    try:
        # Đọc danh sách nodes từ model.inp
        with open(INP_FILE, "r") as f:
            content = f.read()
        
        # Đọc tọa độ từ phần COORDINATES
        coordinates = {}
        coords_pattern = r'\[COORDINATES\](.*?)(?=\[|\Z)'
        coords_match = re.search(coords_pattern, content, re.DOTALL)
        if coords_match:
            coords_content = coords_match.group(1)
            coord_pattern = r'^([A-Za-z0-9_]+)\s+([0-9.-]+)\s+([0-9.-]+)'
            for match in re.finditer(coord_pattern, coords_content, re.MULTILINE):
                node_id = match.group(1)
                if not node_id.startswith(';;'):
                    try:
                        x_coord = float(match.group(2))
                        y_coord = float(match.group(3))
                        coordinates[node_id] = (x_coord, y_coord)
                    except (ValueError, IndexError):
                        pass
        
        logger.info(f"Loaded {len(coordinates)} coordinates from INP file")
        
        nodes = []
        
        # Tìm trong [JUNCTIONS]
        junctions_pattern = r'\[JUNCTIONS\](.*?)(?=\[|\Z)'
        junctions_match = re.search(junctions_pattern, content, re.DOTALL)
        if junctions_match:
            junctions_content = junctions_match.group(1)
            node_pattern = r'^([A-Za-z0-9_]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
            for match in re.finditer(node_pattern, junctions_content, re.MULTILINE):
                node_id = match.group(1)
                if not node_id.startswith(';;'):
                    try:
                        invert_elevation = float(match.group(2))
                        max_depth = float(match.group(3))
                        initial_depth = float(match.group(4))
                        ground_elevation = invert_elevation + max_depth
                        
                        # Sử dụng tọa độ thực từ file INP nếu có
                        x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                        
                        nodes.append({
                            "node_id": node_id,
                            "node_type": "JUNCTION",
                            "x_coordinate": x_coord,
                            "y_coordinate": y_coord,
                            "invert_elevation": invert_elevation,
                            "ground_elevation": ground_elevation,
                            "max_depth": max_depth,
                            "initial_depth": initial_depth
                        })
                    except (ValueError, IndexError):
                        # Nếu không parse được tọa độ, dùng giá trị mặc định
                        # Sử dụng tọa độ thực từ file INP nếu có
                        x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                        
                        nodes.append({
                            "node_id": node_id,
                            "node_type": "JUNCTION",
                            "x_coordinate": x_coord,
                            "y_coordinate": y_coord,
                            "invert_elevation": -2.0,
                            "ground_elevation": 5.0,
                            "max_depth": 7.0,
                            "initial_depth": 0.0
                        })
        
        # Tìm trong [STORAGE]
        storage_pattern = r'\[STORAGE\](.*?)(?=\[|\Z)'
        storage_match = re.search(storage_pattern, content, re.DOTALL)
        if storage_match:
            storage_content = storage_match.group(1)
            node_pattern = r'^([A-Za-z0-9_]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
            for match in re.finditer(node_pattern, storage_content, re.MULTILINE):
                node_id = match.group(1)
                if not node_id.startswith(';;'):
                    try:
                        invert_elevation = float(match.group(2))
                        max_depth = float(match.group(3))
                        initial_depth = float(match.group(4))
                        ground_elevation = invert_elevation + max_depth
                        
                        # Sử dụng tọa độ thực từ file INP nếu có
                        x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                        
                        nodes.append({
                            "node_id": node_id,
                            "node_type": "STORAGE",
                            "x_coordinate": x_coord,
                            "y_coordinate": y_coord,
                            "invert_elevation": invert_elevation,
                            "ground_elevation": ground_elevation,
                            "max_depth": max_depth,
                            "initial_depth": initial_depth
                        })
                    except (ValueError, IndexError):
                        # Sử dụng tọa độ thực từ file INP nếu có
                        x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                        
                        nodes.append({
                            "node_id": node_id,
                            "node_type": "STORAGE",
                            "x_coordinate": x_coord,
                            "y_coordinate": y_coord,
                            "invert_elevation": -2.0,
                            "ground_elevation": 5.0,
                            "max_depth": 7.0,
                            "initial_depth": 0.0
                        })
        
        return {
            "success": True,
            "data": nodes,
            "count": len(nodes)
        }
    except Exception as e:
        logger.error(f"Failed to get available nodes: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get available nodes: {str(e)}",
            "data": []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1433)