import yaml
import os
import shutil
from datetime import datetime

def safe_read_yaml(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def safe_write_yaml(file_path, data, backup=True):
    if backup and os.path.exists(file_path):
        backup_dir = os.path.join(os.path.dirname(file_path), 'backups', datetime.now().strftime('%Y%m%d'))
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2(file_path, os.path.join(backup_dir, f"{os.path.basename(file_path)}.{datetime.now().strftime('%H%M%S')}.bak"))
    
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    return True

def revert_yaml(file_path):
    backup_dir_parent = os.path.join(os.path.dirname(file_path), 'backups')
    if not os.path.exists(backup_dir_parent):
        return False
    
    # Find latest backup
    backups = []
    for root, dirs, files in os.walk(backup_dir_parent):
        for f in files:
            if f.startswith(os.path.basename(file_path)) and f.endswith('.bak'):
                backups.append(os.path.join(root, f))
    
    if not backups:
        return False
    
    latest_backup = max(backups, key=os.path.getmtime)
    shutil.copy2(latest_backup, file_path)
    return True
