"""
SWMM service for SWMM Service v2
Core simulation logic extracted from main_old.py
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from pyswmm import Simulation, Nodes
from ..models.timeseries import TimeseriesInput
from ..services.timeseries_service import interpolate_ts
from ..utils.file_utils import ensure_file_exists
from ..config.settings import settings

logger = logging.getLogger(__name__)


def write_inp(timeseries: TimeseriesInput) -> str:
    """
    Write timeseries data to INP file (from main_old.py)
    
    Args:
        timeseries: TimeseriesInput object
        
    Returns:
        Path to the generated INP file
    """
    with open(settings.get_inp_file_path(), "r", encoding='utf-8') as f:
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

    with open(settings.get_temp_inp_file_path(), "w", encoding='utf-8') as f:
        f.write(full_inp)

    return full_inp


def run_and_parse_swmm() -> List[Dict[str, Any]]:
    """
    Run SWMM simulation and parse results (from main_old.py)
    
    Returns:
        List of simulation results for each node
    """
    try:
        # Đảm bảo đường dẫn tới file temp_model.inp là chính xác
        inp_file_path = settings.get_temp_inp_file_path()
        
        # Kiểm tra xem file có tồn tại không
        if not ensure_file_exists(inp_file_path, settings.get_inp_file_path()):
            raise Exception(f"Neither temp_model.inp nor model.inp found")
        
        # Log thông tin file trước khi chạy
        file_size = os.path.getsize(inp_file_path)
        logger.info(f"Running SWMM simulation with {inp_file_path} (size: {file_size} bytes)...")
        
        # Kiểm tra xem có file cache không
        cache_file = settings.CACHE_FILE
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
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
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2)
                
                # Lưu kết quả vào file debug
                debug_output_path = os.path.join(os.path.dirname(cache_file), "swmm_debug_output.json")
                try:
                    with open(debug_output_path, "w", encoding='utf-8') as f:
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
