
import os
import json
from pyswmm import Simulation, Nodes
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_swmm(inp_file):
    try:
        logger.info(f"Running SWMM simulation with {inp_file}")
        with Simulation(inp_file) as sim:
            all_results = []
            nodes = Nodes(sim)
            
            # Create dictionary to store data for all nodes
            node_list = list(nodes)
            node_data = {node.nodeid: {"depths": [], "invert_elev": node.invert_elevation} for node in node_list}
            
            logger.info(f"Found {len(node_list)} nodes in the model")
            
            # Run simulation and collect data
            step_count = 0
            last_saved_time = None
            
            # Log start and end time
            start_time = sim.start_time
            end_time = sim.end_time
            logger.info(f"Simulation period: {start_time} to {end_time}")
            
            # Run model step by step
            for step in sim:
                step_count += 1
                current_time = sim.current_time
                current_hour = current_time.strftime("%m/%d/%Y %H:00")
                
                # Save data hourly or every 15 minutes
                should_save = (current_time.minute == 0) or (current_time.minute % 15 == 0)
                
                if should_save and (last_saved_time is None or current_hour != last_saved_time):
                    for node in node_list:
                        node_id = node.nodeid
                        depth = float(node.depth)
                        inflow = float(getattr(node, 'total_inflow', 0.0))
                        head = float(getattr(node, 'head', node.invert_elevation + depth))
                        invert_elev = float(node.invert_elevation)
                        
                        # Calculate water level (head = invert_elevation + depth)
                        # head is absolute water level, depth is water depth
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

            # Create results for each node
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
            return all_results
    except Exception as e:
        logger.error(f"SWMM simulation failed: {str(e)}")
        return []

if __name__ == "__main__":
    import sys
    inp_file = sys.argv[1]
    output_file = sys.argv[2]
    
    results = run_swmm(inp_file)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")
