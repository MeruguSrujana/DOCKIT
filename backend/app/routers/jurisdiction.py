from fastapi import APIRouter, Query
from typing import List, Optional

from ..data.telangana_jurisdiction import JURISDICTION_TREE

router = APIRouter(prefix="/jurisdiction", tags=["jurisdiction"])


@router.get("/districts", response_model=List[str])
def list_districts():
    return sorted(JURISDICTION_TREE.keys())


@router.get("/mandals", response_model=List[str])
def list_mandals(district: str = Query(...)):
    return sorted(JURISDICTION_TREE.get(district, {}).keys())


@router.get("/police-stations", response_model=List[str])
def list_police_stations(district: str = Query(...), mandal: str = Query(...)):
    entry = JURISDICTION_TREE.get(district, {}).get(mandal)
    return entry["police_stations"] if entry else []


@router.get("/revenue-offices", response_model=List[str])
def list_revenue_offices(district: str = Query(...), mandal: str = Query(...)):
    entry = JURISDICTION_TREE.get(district, {}).get(mandal)
    return entry["revenue_offices"] if entry else []
