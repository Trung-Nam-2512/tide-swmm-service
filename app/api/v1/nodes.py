"""
Node API endpoints for SWMM Service v2
Extracted from main_old.py
"""

import logging
from fastapi import APIRouter, HTTPException
from ...services.node_service import get_available_nodes
from ...utils.swmm_utils import get_node_detailed_info
from ...config.settings import settings

logger = logging.getLogger(__name__)

# Create router
nodes_router = APIRouter()


@nodes_router.get("/node-info/{node_id}")
def get_node_info(node_id: str):
    """Get detailed information for a specific node (from main_old.py)"""
    try:
        node_info = get_node_detailed_info(node_id, settings.get_inp_file_path())
        return {
            "success": True,
            "data": node_info
        }
    except Exception as e:
        logger.error(f"Failed to get node info for {node_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get node info: {str(e)}")


@nodes_router.get("/flood-risk-summary")
def get_flood_risk_summary():
    """Get flood risk summary for all nodes (from main_old.py)"""
    try:
        # Lấy danh sách nodes
        nodes_response = get_available_nodes()
        if not nodes_response["success"]:
            return {
                "success": False,
                "message": "Failed to get available nodes",
                "data": []
            }
        
        nodes = nodes_response["data"]
        summary = []
        
        for node in nodes:
            node_id = node["node_id"]
            ground_elevation = node.get("ground_elevation", 0)
            invert_elevation = node.get("invert_elevation", 0)
            max_depth = node.get("max_depth", 0)
            
            # Tính nguy cơ ngập dựa trên thông tin cơ bản
            if ground_elevation > invert_elevation:
                flood_ratio = max_depth / (ground_elevation - invert_elevation)
            else:
                flood_ratio = max_depth / 25.0  # Fallback
            
            if flood_ratio <= 0.3:
                risk_level = "LOW"
            elif flood_ratio <= 0.6:
                risk_level = "MEDIUM"
            elif flood_ratio <= 0.85:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"
            
            summary.append({
                "node_id": node_id,
                "node_type": node.get("node_type", "JUNCTION"),
                "ground_elevation": ground_elevation,
                "invert_elevation": invert_elevation,
                "max_depth": max_depth,
                "flood_ratio": flood_ratio,
                "risk_level": risk_level
            })
        
        return {
            "success": True,
            "data": summary,
            "count": len(summary)
        }
        
    except Exception as e:
        logger.error(f"Failed to get flood risk summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get flood risk summary: {str(e)}")
