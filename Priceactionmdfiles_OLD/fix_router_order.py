
import os

TARGET_FILE = '../AlgoTradingTelegramBotAndFrontend/backend/server.py'

def fix_router_inclusion():
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    clean_lines = []
    inclusion_line = ""
    for line in lines:
        if 'app.include_router(api_router)' in line:
            inclusion_line = line
        else:
            clean_lines.append(line)
            
    if inclusion_line:
        # Append inclusion line at the very end
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.writelines(clean_lines)
            f.write('\n' + inclusion_line + '\n')
        print("Successfully moved app.include_router to the end of server.py")
    else:
        print("Could not find app.include_router call.")

if __name__ == "__main__":
    fix_router_inclusion()
