"""
SWMM service for running simulations
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, List
import pyswmm
from ..config.settings import Settings
from ..schemas.timeseries import TimeseriesInput

logger = logging.getLogger(__name__)


class SWMMService:
    """Service for running SWMM simulations"""
    
    def __init__(self):
        self.settings = Settings()
        self.temp_inp_file = self.settings.TEMP_INP_FILE
        self.temp_rpt_file = os.path.join(os.path.dirname(self.temp_inp_file), "temp_model.rpt")
        self.temp_out_file = os.path.join(os.path.dirname(self.temp_inp_file), "temp_model.out")
    
    def _interpolate_ts(self, ts_dict):
        """Interpolate timeseries data (exactly like main_old.py)"""
        if not ts_dict:
            return {}
        import pandas as pd
        import numpy as np
        from datetime import datetime
        
        times = sorted([datetime.strptime(t, "%m/%d/%Y %H:%M") for t in ts_dict.keys()])
        values = [ts_dict[times[i].strftime("%m/%d/%Y %H:%M")] for i in range(len(times))]
        full_times = pd.date_range(times[0], times[-1], freq="H")  # Changed from "h" to "H" to match main_old.py
        interp_values = np.interp([t.timestamp() for t in full_times], [t.timestamp() for t in times], values)
        return {full_times[i].strftime("%m/%d/%Y %H:%M"): interp_values[i] for i in range(len(full_times))}
    
    def write_inp_file(self, timeseries: TimeseriesInput) -> str:
        """
        Write timeseries data to INP file
        
        Args:
            timeseries: TimeseriesInput object with all timeseries data
            
        Returns:
            Path to the generated INP file
        """
        try:
            # Read base INP file
            with open(self.settings.INP_FILE, 'r', encoding='utf-8') as f:
                base_inp = f.read()
            
            # Interpolate tất cả timeseries (exactly like main_old.py)
            timeseries.rain = self._interpolate_ts(timeseries.rain)
            timeseries.inflow_dautieng = self._interpolate_ts(timeseries.inflow_dautieng)
            timeseries.inflow_trian = self._interpolate_ts(timeseries.inflow_trian)
            timeseries.tide = self._interpolate_ts(timeseries.tide)
            
            # Format TIMESERIES sections (exactly like main_old.py)
            tsn = "\n".join([f"TSN   {dt}   {val}" for dt, val in timeseries.rain.items()])
            inflow_dt = "\n".join([f"Inflow_DauTieng   {dt}   {val}" for dt, val in timeseries.inflow_dautieng.items()])
            inflow_ta = "\n".join([f"Inflow_TriAn   {dt}   {val}" for dt, val in timeseries.inflow_trian.items()])
            vt = "\n".join([f"VT   {dt}   {val}" for dt, val in timeseries.tide.items()])
            
            # Create INFLOWS section (theo format của main_old.py)
            inflows_section = f"""[INFLOWS]
;;Node           Constituent      Time Series      Type    Mfactor  Sfactor
0SG              FLOW             Inflow_DauTieng  FLOW    1.0      1.0
0DN              FLOW             Inflow_TriAn     FLOW    1.0      1.0
"""
            
            # Create TIMESERIES section (theo format của main_old.py)
            timeseries_section = f"""[TIMESERIES]
{tsn}
{inflow_dt}
{inflow_ta}
{vt}
"""
            
            # Remove old TIMESERIES and INFLOWS sections (like main_old.py)
            base_inp = re.sub(r'\[TIMESERIES\].*?(?=\[|$)', '', base_inp, flags=re.DOTALL)
            base_inp = re.sub(r'\[INFLOWS\].*?(?=\[|$)', '', base_inp, flags=re.DOTALL)
            
            # Add new sections at the end of file (like main_old.py)
            base_inp = base_inp.rstrip() + "\n\n" + inflows_section + timeseries_section
            
            # Write to temp file
            with open(self.temp_inp_file, 'w', encoding='utf-8') as f:
                f.write(base_inp)
            
            logger.info(f"INP file written to: {self.temp_inp_file}")
            return self.temp_inp_file
            
        except Exception as e:
            logger.error(f"Error writing INP file: {str(e)}")
            raise
    
    def run_simulation(self) -> List[Dict[str, Any]]:
        """
        Run SWMM simulation and return results (matching main_old.py logic)
        
        Returns:
            List of simulation results for each node
        """
        try:
            # Run simulation using PySWMM Nodes class (like main_old.py)
            with pyswmm.Simulation(self.temp_inp_file) as sim:
                all_results = []
                nodes = pyswmm.Nodes(sim)
                
                # Create dictionary to store data for all nodes (like main_old.py)
                node_list = list(nodes)
                node_data = {node.nodeid: {"depths": [], "invert_elev": node.invert_elevation} for node in node_list}
                
                logger.info(f"Found {len(node_list)} nodes in the model")
                
                # Run simulation and collect data
                step_count = 0
                last_saved_time = None
                
                # Log start and end time of the model
                start_time = sim.start_time
                end_time = sim.end_time
                logger.info(f"Simulation period: {start_time} to {end_time}")
                
                # Run model step by step
                for step in sim:
                    step_count += 1
                    current_time = sim.current_time
                    current_hour = current_time.strftime("%m/%d/%Y %H:00")
                    
                    # Save data every hour (when minute = 0) or every 15 minutes
                    should_save = (current_time.minute == 0) or (current_time.minute % 15 == 0)
                    
                    if should_save and (last_saved_time is None or current_hour != last_saved_time):
                        for node in node_list:
                            node_id = node.nodeid
                            depth = float(node.depth)
                            inflow = float(getattr(node, 'total_inflow', 0.0))
                            head = float(getattr(node, 'head', node.invert_elevation + depth))
                            invert_elev = float(node.invert_elevation)
                            
                            # Calculate water level by elevation (head = invert_elevation + depth)
                            # head is absolute water surface elevation, depth is water depth
                            water_level = head
                            
                            node_data[node_id]["depths"].append({
                                "time": current_hour,
                                "depth": depth,
                                "inflow": inflow,
                                "water_level": water_level,
                                "invert_elevation": invert_elev
                            })
                        
                        last_saved_time = current_hour
                        
                        # Log progress every 24 hours
                        if step_count % 96 == 0:  # 24 hours * 4 (15 minutes per step)
                            logger.info(f"Simulation progress: {current_time} (step {step_count})")
                
                logger.info(f"Simulation completed with {step_count} steps")

                # Create results for each node (like main_old.py)
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
                
                # Save results to JSON file
                import json
                with open(self.temp_out_file.replace('.out', '.json'), 'w') as f:
                    json.dump(all_results, f, indent=2)
                
                return all_results
                
        except Exception as e:
            logger.error(f"Error running simulation: {str(e)}")
            raise
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_files = [self.temp_inp_file, self.temp_rpt_file, self.temp_out_file]
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")
