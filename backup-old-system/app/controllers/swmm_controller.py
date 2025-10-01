"""
SWMM controller for handling simulation requests
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException
from ..schemas.timeseries import TimeseriesInput, SimulationInput
from ..services.swmm_service import SWMMService
from ..utils.file_utils import FileUtils

logger = logging.getLogger(__name__)


class SWMMController:
    """Controller for SWMM simulation operations"""
    
    def __init__(self):
        self.swmm_service = SWMMService()
        self.file_utils = FileUtils()
    
    def run_swmm_simulation(self, timeseries: TimeseriesInput) -> Dict[str, Any]:
        """
        Run SWMM simulation with timeseries data
        
        Args:
            timeseries: TimeseriesInput object
            
        Returns:
            Dictionary with simulation results
        """
        try:
            # Write INP file
            self.swmm_service.write_inp_file(timeseries)
            
            # Run simulation
            results = self.swmm_service.run_simulation()
            
            return {"results": results}
            
        except Exception as e:
            logger.error(f"Error running SWMM simulation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"SWMM simulation failed: {str(e)}")
        finally:
            # Cleanup temporary files
            self.file_utils.cleanup_temp_files([
                "temp_model.inp", 
                "temp_model.rpt", 
                "temp_model.out"
            ])
    
    def run_custom_simulation(self, simulation_input: SimulationInput) -> Dict[str, Any]:
        """
        Run custom simulation with user-defined data
        
        Args:
            simulation_input: SimulationInput object
            
        Returns:
            Dictionary with simulation results
        """
        try:
            logger.info(f"Running custom simulation: {simulation_input.simulation_name}")
            
            # Convert frontend data to TimeseriesInput format
            timeseries_data = TimeseriesInput(
                rain={item["time"]: item["value"] for item in simulation_input.timeseries.get("rainfall", [])},
                inflow_dautieng={item["time"]: item["value"] for item in simulation_input.timeseries.get("dauTieng", [])},
                inflow_trian={item["time"]: item["value"] for item in simulation_input.timeseries.get("triAn", [])},
                tide={item["time"]: item["value"] for item in simulation_input.timeseries.get("tide", [])}
            )
            
            # Write custom INP file
            inp_content = self.swmm_service.write_inp_file(timeseries_data)
            
            # Save custom INP file
            import os
            custom_inp_path = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                f"custom_{simulation_input.simulation_name.replace(' ', '_')}.inp"
            )
            with open(custom_inp_path, 'w') as f:
                f.write(inp_content)
            
            logger.info(f"Custom INP file created: {custom_inp_path}")
            
            # Run simulation with custom file
            results = self.swmm_service.run_simulation(custom_inp_path)
            
            # Save results to JSON file
            import json
            from datetime import datetime
            
            results_file = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                f"custom_results_{simulation_input.simulation_name.replace(' ', '_')}.json"
            )
            
            with open(results_file, 'w') as f:
                json.dump({
                    "simulation_name": simulation_input.simulation_name,
                    "start_date": simulation_input.start_date,
                    "end_date": simulation_input.end_date,
                    "time_step": simulation_input.time_step,
                    "results": results,
                    "created_at": datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"Custom simulation results saved to: {results_file}")
            
            return {
                "success": True,
                "simulation_name": simulation_input.simulation_name,
                "results": results,
                "total_nodes": len(results),
                "results_file": results_file
            }
            
        except Exception as e:
            logger.error(f"Error running custom simulation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error running custom simulation: {str(e)}")
