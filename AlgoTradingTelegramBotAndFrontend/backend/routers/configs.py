from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import glob
from utils.yaml_io import safe_read_yaml, safe_write_yaml, revert_yaml

router = APIRouter(prefix="/api/configs", tags=["configs"])

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "config")

@router.get("/list")
def list_configs():
    files = glob.glob(os.path.join(CONFIG_DIR, "*.yaml"))
    return {"configs": [os.path.basename(f) for f in files]}

@router.get("/{name}")
def get_config(name: str):
    file_path = os.path.join(CONFIG_DIR, name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Config not found")
    data = safe_read_yaml(file_path)
    return {"name": name, "data": data}

class ConfigUpdate(BaseModel):
    data: dict

@router.post("/{name}")
def update_config(name: str, update: ConfigUpdate):
    file_path = os.path.join(CONFIG_DIR, name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Config not found")
    
    success = safe_write_yaml(file_path, update.data)
    if success:
        return {"status": "success", "message": f"Updated {name}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to write config")

@router.post("/{name}/revert")
def revert_config(name: str):
    file_path = os.path.join(CONFIG_DIR, name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Config not found")
    
    success = revert_yaml(file_path)
    if success:
        return {"status": "success", "message": f"Reverted {name}"}
    else:
        raise HTTPException(status_code=404, detail="No backup found to revert to")
