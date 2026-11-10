import re
import os

def read_v3_utils_constants():
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules', 'v3_utils.py')
    if not os.path.exists(file_path):
        return {}
    
    constants = {}
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Match CAPS_CONSTANTS = VALUE
    matches = re.findall(r'^([A-Z][A-Z0-9_]+)\s*=\s*(.+)$', content, re.MULTILINE)
    for name, value in matches:
        try:
            # Basic evaluation for common types
            val = value.strip().split('#')[0].strip() # Remove comments
            if val.lower() == 'true':
                constants[name] = True
            elif val.lower() == 'false':
                constants[name] = False
            elif val.startswith("'") or val.startswith('"'):
                constants[name] = val.strip("'\"")
            elif '.' in val:
                constants[name] = float(val)
            else:
                constants[name] = int(val)
        except:
            constants[name] = val # Keep as string if parsing fails
            
    return constants

def update_v3_utils_constant(name, new_value):
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules', 'v3_utils.py')
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{name} =") or line.startswith(f"{name}="):
            if isinstance(new_value, str):
                formatted_value = f"'{new_value}'"
            else:
                formatted_value = str(new_value)
            new_lines.append(f"{name} = {formatted_value}\n")
            found = True
        else:
            new_lines.append(line)
            
    if found:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        return True
    return False
