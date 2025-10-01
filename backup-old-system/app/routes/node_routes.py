"""
Node routes for node-related endpoints
"""

from fastapi import APIRouter, Query
from ..controllers.node_controller import NodeController

# Create router
node_router = APIRouter(prefix="/swmm-api", tags=["Nodes"])

# Initialize controller
node_controller = NodeController()


@node_router.get("/available-nodes")
def get_available_nodes():
    """
    Get list of all available nodes with coordinates
    
    Returns:
        Dictionary with node list
    """
    return node_controller.get_available_nodes()


@node_router.get("/node-info/{node_id}")
def get_node_info(node_id: str):
    """
    Get detailed information for a specific node
    
    Args:
        node_id: Node ID to get info for
        
    Returns:
        Dictionary with node information
    """
    return node_controller.get_node_info(node_id)


@node_router.get("/flood-risk-summary")
def get_flood_risk_summary(
    start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
    end_date: str = Query(..., description="End date (MM/DD/YYYY)")
):
    """
    Get flood risk summary for all nodes
    
    Args:
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format
        
    Returns:
        Dictionary with flood risk summary
    """
    return node_controller.get_flood_risk_summary(start_date, end_date)
