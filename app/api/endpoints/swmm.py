"""
SWMM simulation endpoints (chuẩn hoá: sync/async + status + result)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Response, status
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Union

# >>> Điều chỉnh import đúng theo cây dự án của bạn
from ...models.schemas import (
    SWMMSimulationRequest,           # chứa start_date, end_date
    SWMMForecastRequest,             # chứa start_date, end_date, use_real_data
    SWMMSimulationResult,            # kết quả tóm tắt
    DetailedSWMMResult,              # kết quả chi tiết theo node
    SimulationStatus     ,
    ManualSWMMInput             # schema trạng thái
)
from ...services.swmm_service_corrected import CorrectedSWMMService

router = APIRouter()

# ====== Bộ nhớ tạm cho job (prod nên dùng Redis/DB) ======
class JobState(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"

# Lưu ý: in-memory -> chỉ áp dụng khi chạy 1 worker
JOBS: Dict[str, Dict[str, Any]] = {}


# ========= Helpers =========
def _new_job() -> str:
    sim_id = str(uuid.uuid4())
    JOBS[sim_id] = {
        "status": JobState.queued.value,
        "progress": 0.0,
        "start_time": datetime.now(),
        "error_message": None,
        "result": None,
        "detailed": False,
    }
    return sim_id


async def _run_and_store(sim_id: str, req: SWMMForecastRequest, detailed_output: bool):
    JOBS[sim_id]["status"] = JobState.running.value
    JOBS[sim_id]["progress"] = 10.0
    JOBS[sim_id]["detailed"] = detailed_output

    try:
        svc = CorrectedSWMMService()
        result = await svc.run_forecast_simulation(
            start_date=req.start_date,
            end_date=req.end_date,
            use_real_data=req.use_real_data,
            detailed_output=detailed_output,
        )
        # Lưu ở dạng dict để JSON-serializable (Pydantic v2)
        JOBS[sim_id]["result"] = result.model_dump()
        JOBS[sim_id]["status"] = JobState.succeeded.value
        JOBS[sim_id]["progress"] = 100.0
        JOBS[sim_id]["end_time"] = datetime.now()
    except Exception as e:
        JOBS[sim_id]["status"] = JobState.failed.value
        JOBS[sim_id]["error_message"] = str(e)
        JOBS[sim_id]["end_time"] = datetime.now()


# ========= Endpoints =========

@router.post(
    "/run",
    responses={
        200: {"description": "Sync: trả về kết quả ngay"},
        202: {"description": "Async: đã xếp hàng, trả về simulation_id"},
    },
)
async def run_swmm(
    request: SWMMForecastRequest,
    response: Response,
    mode: str = Query("sync", pattern="^(sync|async)$"),
    detailed_output: bool = Query(False),
):
    """
    Chạy mô phỏng SWMM.
    - mode=sync  -> chờ chạy xong và trả về kết quả ngay (200)
    - mode=async -> chạy background, trả về simulation_id (202) để gọi /status và /result
    - detailed_output=true -> trả về kiểu DetailedSWMMResult (node-level)
    """
    try:
        if mode == "sync":
            svc = CorrectedSWMMService()
            result = await svc.run_forecast_simulation(
                start_date=request.start_date,
                end_date=request.end_date,
                use_real_data=request.use_real_data,
                detailed_output=detailed_output,
            )
            # Trả về theo đúng model tương ứng
            if detailed_output:
                response.status_code = status.HTTP_200_OK
                return DetailedSWMMResult(**result.model_dump())
            else:
                response.status_code = status.HTTP_200_OK
                return SWMMSimulationResult(**result.model_dump())

        # mode == "async"
        sim_id = _new_job()
        # lưu lại tham số để tiện debug (tuỳ chọn)
        JOBS[sim_id]["params"] = {
            "start_date": request.start_date,
            "end_date": request.end_date,
            "use_real_data": request.use_real_data,
            "detailed_output": detailed_output,
        }

        # chạy nền
        bg_service = BackgroundTasks()
        bg_service.add_task(_run_and_store, sim_id, request, detailed_output)
        # trick: trả tasks về để FastAPI enqueue
        response.background = bg_service

        # 202 Accepted + Location gợi ý
        response.status_code = status.HTTP_202_ACCEPTED
        response.headers["Location"] = f"/api/v1/swmm/status/{sim_id}"
        return {
            "message": "Simulation started",
            "simulation_id": sim_id,
            "status": JobState.running.value,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Run failed: {str(e)}")


@router.get("/status/{simulation_id}", response_model=SimulationStatus)
async def get_status(simulation_id: str):
    job = JOBS.get(simulation_id)
    if not job:
        raise HTTPException(404, "Simulation not found")

    return SimulationStatus(
        simulation_id=simulation_id,
        status=job["status"],
        progress=job.get("progress"),
        start_time=job.get("start_time"),
        estimated_completion=job.get("estimated_completion"),
        error_message=job.get("error_message"),
    )


@router.get("/result/{simulation_id}")
async def get_result(simulation_id: str):
    job = JOBS.get(simulation_id)
    if not job:
        raise HTTPException(404, "Simulation not found")

    if job["status"] != JobState.succeeded.value:
        # Trả về trạng thái hiện tại (chưa xong)
        return {
            "simulation_id": simulation_id,
            "status": job["status"],
            "error": job.get("error_message"),
        }

    # Trả đúng model theo cờ detailed đã chạy
    data = job["result"]  # dict đã model_dump
    if job.get("detailed"):
        return DetailedSWMMResult(**data)
    else:
        return SWMMSimulationResult(**data)


@router.get("/model-info", response_model=Dict[str, Any])
async def model_info():
    try:
        svc = CorrectedSWMMService()
        return svc.get_model_info()
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/health")
async def swmm_health():
    """SWMM service health check"""
    try:
        svc = CorrectedSWMMService()
        return {
            "service": "SWMM Service",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "model_ready": True
        }
    except Exception as e:
        raise HTTPException(500, f"SWMM service unhealthy: {str(e)}")

@router.post("/execute-full")
async def execute_full_simulation(
    request: SWMMForecastRequest,
    detailed_output: bool = Query(True, description="Return detailed node-level results"),
    max_nodes: int = Query(100, description="Maximum number of nodes to return in detailed mode", ge=1, le=200),
    time_step_hours: int = Query(2, description="Time step interval in hours for detailed results", ge=1, le=24)
):
    """Execute complete SWMM simulation with full integration
    
    OPTIMIZATION NOTES:
    - detailed_output=False: Returns summary only (recommended for large simulations)
    - detailed_output=True: Returns per-node data with pagination controls
    - max_nodes: Limits number of nodes returned (default: 50)
    - time_step_hours: Reduces time resolution (default: 6 hours)
    """
    try:
        svc = CorrectedSWMMService()
        
        # For detailed output, apply optimizations
        if detailed_output:
            # Limit simulation period for detailed results to prevent huge responses
            max_hours = 48  # 2 days max for detailed results
            sim_duration = (request.end_date - request.start_date).total_seconds() / 3600
            
            if sim_duration > max_hours:
                # Truncate to max_hours
                request.end_date = request.start_date + timedelta(hours=max_hours)
                logger.warning(f"⚠️ Detailed output limited to {max_hours}h to prevent huge response")
        
        result = await svc.run_forecast_simulation(
            start_date=request.start_date,
            end_date=request.end_date,
            use_real_data=request.use_real_data,
            detailed_output=detailed_output,
        )
        
        # Apply post-processing optimizations for detailed results
        if detailed_output and hasattr(result, 'node_predictions') and result.node_predictions:
            result = svc._optimize_detailed_response(result, max_nodes, time_step_hours)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full simulation failed: {str(e)}")

@router.post("/execute-summary")
async def execute_summary_simulation(
    request: SWMMForecastRequest
):
    """Execute SWMM simulation with summary results only (optimized for large simulations)"""
    try:
        svc = CorrectedSWMMService()
        result = await svc.run_forecast_simulation(
            start_date=request.start_date,
            end_date=request.end_date,
            use_real_data=request.use_real_data,
            detailed_output=False,  # Always summary for this endpoint
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary simulation failed: {str(e)}")

@router.post("/run-manual", response_model=Union[DetailedSWMMResult, SWMMSimulationResult])
async def run_swmm_manual(
    payload: ManualSWMMInput,
    detailed_output: bool = Query(False, description="Trả chi tiết per-node nếu true")
):
    """
    Chạy SWMM chỉ với 2 đầu vào: rainfall + water_level do client cấp.
    KHÔNG lấy/ghép dữ liệu từ các nguồn khác.
    """
    try:
        swmm_service = CorrectedSWMMService()
        result = await swmm_service.run_with_manual_inputs(
            start_date=payload.start_date,
            end_date=payload.end_date,
            rainfall=payload.rainfall,
            water_level=payload.water_level,
            detailed_output=detailed_output
        )
        # result đã là model pydantic
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual run failed: {str(e)}")

@router.post("/comprehensive-test")
async def run_comprehensive_test(
    test_hours: int = Query(24, description="Số giờ để test (default: 24h)", ge=1, le=72)
):
    """
    🧪 COMPREHENSIVE SYSTEM TEST
    
    Test toàn bộ hệ thống end-to-end với dữ liệu thực:
    - Tất cả API connections
    - SWMM simulation với real data
    - Physics validation
    - Performance metrics
    """
    try:
        svc = CorrectedSWMMService()
        test_results = await svc.comprehensive_system_test(test_hours=test_hours)
        
        return {
            "message": f"Comprehensive system test completed: {test_results['overall_status']}",
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System test failed: {str(e)}")

@router.get("/data-quality-check")
async def data_quality_check():
    """
    🔍 DATA QUALITY CHECK
    
    Kiểm tra chất lượng tất cả nguồn dữ liệu thực
    Không chạy simulation, chỉ validate APIs
    """
    try:
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_period_hours": 6,
            "api_status": {},
            "overall_data_health": "UNKNOWN",
            "debug_info": []
        }
        
        # Initialize service safely
        try:
            svc = CorrectedSWMMService()
            data_service = svc.data_service
            now = datetime.now()
            test_period = now + timedelta(hours=6)
            results["debug_info"].append("✅ SWMMService initialized successfully")
        except Exception as init_error:
            results["debug_info"].append(f"❌ SWMMService initialization failed: {init_error}")
            results["overall_data_health"] = "CRITICAL"
            return results
        
        # Test Ho Dau Tieng
        try:
            hdt_data = await data_service.fetch_ho_dau_tieng_forecast_data(now, test_period)
            results["api_status"]["ho_dau_tieng"] = {
                "status": "HEALTHY" if hdt_data.get("inflow") else "NO_DATA",
                "records": len(hdt_data.get("inflow", [])),
                "last_update": hdt_data.get("inflow", [{}])[-1].get("data_thoigian") if hdt_data.get("inflow") else None
            }
        except Exception as e:
            results["api_status"]["ho_dau_tieng"] = {"status": "ERROR", "error": str(e)}
        
        # Test Vung Tau
        try:
            vt_data = await data_service.fetch_vung_tau_tide_data(now, test_period)
            
            # Calculate tide range safely
            tide_range = {"min": 0, "max": 0, "range": 0}
            if vt_data.get("seamless_series"):
                tide_values = [p.get("tide_cm", 0)/100.0 for p in vt_data["seamless_series"]]
                if tide_values:
                    tide_range = {
                        "min": min(tide_values),
                        "max": max(tide_values),
                        "range": max(tide_values) - min(tide_values)
                    }
            
            results["api_status"]["vung_tau"] = {
                "status": "HEALTHY" if vt_data.get("seamless_series") else "NO_DATA",
                "records": len(vt_data.get("seamless_series", [])),
                "tide_range": tide_range
            }
        except Exception as e:
            results["api_status"]["vung_tau"] = {"status": "ERROR", "error": str(e)}
        
        # Test Rainfall APIs (expect this to fail since we blocked simulation data)
        try:
            rainfall_data = await data_service.fetch_real_rainfall_data(now, test_period)
            results["api_status"]["rainfall"] = {
                "status": "HEALTHY" if rainfall_data else "NO_DATA",
                "records": len(rainfall_data),
                "sources": list(set(r.station_id for r in rainfall_data)) if rainfall_data else []
            }
            results["debug_info"].append("✅ Real rainfall API working")
        except Exception as e:
            # Expected failure - we blocked all simulation rainfall
            error_msg = str(e)
            if "NO_REAL_RAINFALL_DATA" in error_msg or "SIMULATION_DATA_BLOCKED" in error_msg:
                results["api_status"]["rainfall"] = {
                    "status": "BLOCKED_SIMULATION", 
                    "message": "Simulation rainfall blocked - real API needed",
                    "error": error_msg
                }
                results["debug_info"].append("ℹ️ Rainfall simulation data correctly blocked")
            else:
                results["api_status"]["rainfall"] = {"status": "ERROR", "error": error_msg}
                results["debug_info"].append(f"❌ Unexpected rainfall API error: {error_msg}")
        
        # Overall health assessment (account for blocked rainfall simulation)
        healthy_apis = sum(1 for api in results["api_status"].values() if api.get("status") == "HEALTHY")
        blocked_apis = sum(1 for api in results["api_status"].values() if api.get("status") == "BLOCKED_SIMULATION")
        total_apis = len(results["api_status"])
        critical_apis = healthy_apis + blocked_apis  # Blocked simulation is actually good
        
        results["debug_info"].append(f"📊 API Status: {healthy_apis} healthy, {blocked_apis} blocked (expected), {total_apis} total")
        
        if healthy_apis >= 2:  # At least 2 real APIs working (Ho Dau Tieng + Vung Tau)
            results["overall_data_health"] = "EXCELLENT"
            results["debug_info"].append("✅ Excellent: Both boundary APIs working")
        elif healthy_apis >= 1:  # At least 1 real API working
            results["overall_data_health"] = "GOOD" 
            results["debug_info"].append("⚠️ Good: At least one boundary API working")
        elif blocked_apis > 0:  # Only blocked APIs (simulation correctly disabled)
            results["overall_data_health"] = "LIMITED"
            results["debug_info"].append("⚠️ Limited: Real APIs needed, simulation correctly blocked")
        else:
            results["overall_data_health"] = "CRITICAL"
            results["debug_info"].append("❌ Critical: No APIs working")
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data quality check failed: {str(e)}")
