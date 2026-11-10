import os

def audit_codebase():
    root = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options"
    audit_file = 'CODEBASE_AUDIT_REPORT.txt'
    
    print(f"Starting audit in {root}...")
    
    with open(audit_file, 'w', encoding='utf-8') as f:
        f.write("CODEBASE AUDIT REPORT\n")
        f.write("====================\n\n")
        
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip common junk folders
            if any(junk in dirpath for junk in ['__pycache__', '.git', '.venv', '.pytest_cache']):
                continue
                
            for filename in filenames:
                if filename.endswith(('.py', '.md', '.csv', '.json', '.txt', '.yaml', '.yml', '.env', '.toml')):
                    full_path = os.path.join(dirpath, filename)
                    f.write(full_path + "\n")
                    
    print(f"✅ Audit complete. Report saved to {audit_file}")

if __name__ == "__main__":
    audit_codebase()
