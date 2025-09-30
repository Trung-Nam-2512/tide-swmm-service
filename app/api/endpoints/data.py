"""
Data management endpoints - Updated cho 3 API chính xác
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ...models.schemas import RainfallData, WaterLevelData
from ...services.data_service import DataService

router = APIRouter()

@router.get("/test-apis")
async def test_all_apis():
    """Test kết nối với tất cả 3 API nguồn"""
    try:
        data_service = DataService()
        results = await data_service.test_all_apis()
        
        return {
            "success": True,
            "apis": {
                "ho_dau_tieng": {
                    "status": "✅ Connected" if results["ho_dau_tieng"] else "❌ Failed",
                    "description": "Hồ Dầu Tiếng - Upstream Sài Gòn",
                    "endpoints": ["water_level", "inflow", "discharge"]
                },
                "ho_tri_an": {
                    "status": "✅ Connected" if results["ho_tri_an"] else "❌ Failed", 
                    "description": "Hồ Trị An - Upstream Đồng Nai",
                    "endpoints": ["htl", "qve", "qxt", "qxm"]
                },
                "vung_tau": {
                    "status": "✅ Connected" if results["vung_tau"] else "❌ Failed",
                    "description": "Vũng Tàu - Downstream Biển Đông",
                    "endpoints": ["forecast", "realtime"]
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test APIs: {str(e)}")

@router.get("/ho-dau-tieng")
async def get_ho_dau_tieng_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Lấy dữ liệu Hồ Dầu Tiếng (upstream Sài Gòn)"""
    try:
        # Default: 7 ngày gần nhất
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
            
        data_service = DataService()
        ho_dau_tieng_data = await data_service.fetch_ho_dau_tieng_data(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "data": ho_dau_tieng_data,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "water_level_records": len(ho_dau_tieng_data.get("water_level", [])),
                "inflow_records": len(ho_dau_tieng_data.get("inflow", [])),
                "discharge_records": len(ho_dau_tieng_data.get("discharge", []))
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Hồ Dầu Tiếng data: {str(e)}")

@router.get("/ho-tri-an")
async def get_ho_tri_an_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Lấy dữ liệu Hồ Trị An (upstream Đồng Nai)"""
    try:
        # Default: 7 ngày gần nhất
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
            
        data_service = DataService()
        ho_tri_an_data = await data_service.fetch_ho_tri_an_data(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "data": ho_tri_an_data,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "count": len(ho_tri_an_data),
            "fields": list(ho_tri_an_data[0].keys()) if ho_tri_an_data else [],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Hồ Trị An data: {str(e)}")

@router.get("/vung-tau-tide")
async def get_vung_tau_tide_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Lấy dữ liệu thủy triều Vũng Tàu (downstream boundary)"""
    try:
        # Default: 7 ngày gần nhất
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
            
        data_service = DataService()
        vung_tau_data = await data_service.fetch_vung_tau_tide_data(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "data": vung_tau_data,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "forecast_records": len(vung_tau_data.get("forecast", [])),
                "realtime_records": len(vung_tau_data.get("realtime", []))
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Vũng Tàu tide data: {str(e)}")

@router.get("/rainfall", response_model=List[RainfallData])
async def get_rainfall_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    station_id: Optional[str] = None
):
    """Lấy dữ liệu mưa (default cho Hồ Trị An)"""
    try:
        # Default: 24 giờ tới
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=1)
            
        data_service = DataService()
        rainfall_data = await data_service.fetch_rainfall_data(
            start_date=start_date,
            end_date=end_date,
            station_id=station_id
        )
        
        return rainfall_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch rainfall data: {str(e)}")

@router.get("/water-level-converted")
async def get_converted_water_level_data(
    source: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Lấy dữ liệu mực nước đã convert cho SWMM"""
    try:
        if source not in ["ho_dau_tieng", "ho_tri_an", "vung_tau"]:
            raise HTTPException(
                status_code=400, 
                detail="Source must be one of: ho_dau_tieng, ho_tri_an, vung_tau"
            )
            
        # Default: 7 ngày gần nhất
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
            
        data_service = DataService()
        
        # Fetch raw data theo source
        if source == "ho_dau_tieng":
            raw_data = await data_service.fetch_ho_dau_tieng_data(start_date, end_date)
            water_level_data = data_service.convert_to_water_level_data(
                raw_data.get("water_level", []), source
            )
        elif source == "ho_tri_an":
            raw_data = await data_service.fetch_ho_tri_an_data(start_date, end_date)
            water_level_data = data_service.convert_to_water_level_data(raw_data, source)
        else:  # vung_tau
            raw_data = await data_service.fetch_vung_tau_tide_data(start_date, end_date)
            # Combine forecast + realtime
            all_data = raw_data.get("forecast", []) + raw_data.get("realtime", [])
            water_level_data = data_service.convert_to_water_level_data(all_data, source)
        
        return {
            "success": True,
            "data": [data.dict() for data in water_level_data],
            "source": source,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "count": len(water_level_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch converted water level data: {str(e)}")

@router.get("/ho-tri-an/default-rainfall")
async def get_ho_tri_an_default_rainfall():
    """Lấy giá trị mưa mặc định cho Hồ Trị An"""
    try:
        data_service = DataService()
        default_rainfall = data_service.get_ho_tri_an_default_rainfall()
        
        return {
            "success": True,
            "station_name": "Hồ Trị An",
            "default_rainfall_mm_per_day": default_rainfall,
            "description": "Giá trị mưa trung bình sử dụng khi không có dữ liệu dự báo",
            "source": "Phân tích từ dữ liệu lịch sử SWMM model",
            "seasonal_pattern": {
                "wet_season": {
                    "months": "May-October",
                    "base_rainfall": "20-30 mm/day"
                },
                "dry_season": {
                    "months": "November-April", 
                    "base_rainfall": "15-18 mm/day"
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get default rainfall: {str(e)}")

@router.get("/swmm-input-summary")
async def get_swmm_input_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Tổng hợp tất cả dữ liệu đầu vào cho SWMM"""
    try:
        # Default: 24 giờ tới
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=1)
            
        data_service = DataService()
        
        # Fetch all data sources
        ho_dau_tieng_data = await data_service.fetch_ho_dau_tieng_data(start_date, end_date)
        ho_tri_an_data = await data_service.fetch_ho_tri_an_data(start_date, end_date)
        vung_tau_data = await data_service.fetch_vung_tau_tide_data(start_date, end_date)
        rainfall_data = await data_service.fetch_rainfall_data(start_date, end_date)
        
        return {
            "success": True,
            "swmm_input_data": {
                "upstream": {
                    "sai_gon": {
                        "source": "Hồ Dầu Tiếng",
                        "water_level_records": len(ho_dau_tieng_data.get("water_level", [])),
                        "inflow_records": len(ho_dau_tieng_data.get("inflow", [])),
                        "discharge_records": len(ho_dau_tieng_data.get("discharge", []))
                    },
                    "dong_nai": {
                        "source": "Hồ Trị An", 
                        "records": len(ho_tri_an_data),
                        "fields": list(ho_tri_an_data[0].keys()) if ho_tri_an_data else []
                    }
                },
                "downstream": {
                    "boundary": {
                        "source": "Vũng Tàu Tide",
                        "forecast_records": len(vung_tau_data.get("forecast", [])),
                        "realtime_records": len(vung_tau_data.get("realtime", []))
                    }
                },
                "rainfall": {
                    "source": "Hồ Trị An Default Pattern",
                    "records": len(rainfall_data)
                }
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "data_availability": {
                "ho_dau_tieng": bool(ho_dau_tieng_data.get("water_level")),
                "ho_tri_an": bool(ho_tri_an_data),
                "vung_tau": bool(vung_tau_data.get("forecast") or vung_tau_data.get("realtime")),
                "rainfall": True  # Always available (default)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SWMM input summary: {str(e)}")