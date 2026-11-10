import requests
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScripMasterUpdater")

def update_scrip_master():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    file_path = "scrip_master.json"
    
    logger.info(f"Downloading scrip master from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Downloaded {len(data)} scrips. Saving to {file_path}...")
        
        with open(file_path, 'w') as f:
            json.dump(data, f)
            
        logger.info("Scrip master updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to update scrip master: {e}")
        return False

if __name__ == "__main__":
    update_scrip_master()
