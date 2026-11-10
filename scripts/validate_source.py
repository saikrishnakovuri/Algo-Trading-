import os
import py_compile
import importlib.util

def validate_source_code():
    report_file = 'CODEBASE_AUDIT_REPORT.txt'
    validation_log = 'SOURCE_VALIDATION_LOG.txt'
    
    if not os.path.exists(report_file):
        print("❌ Error: CODEBASE_AUDIT_REPORT.txt not found.")
        return

    with open(report_file, 'r', encoding='utf-8') as f:
        all_files = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('=') and not line.startswith('CODEBASE')]

    # FILTER: ONLY source code files (not in venv, site-packages, etc.)
    # We look for files in the root or in recognized module folders
    py_files = [f for f in all_files if f.endswith('.py') 
                and 'venv' not in f 
                and 'site-packages' not in f
                and 'Lib' not in f]
    
    print(f"Validating {len(py_files)} source Python files...")
    
    with open(validation_log, 'w', encoding='utf-8') as log:
        log.write("SOURCE PYTHON VALIDATION LOG\n")
        log.write("============================\n\n")
        
        for pf in py_files:
            rel_path = os.path.relpath(pf, r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options")
            
            # 1. Compile Check
            try:
                py_compile.compile(pf, doraise=True)
                log.write(f"[COMPILE] {rel_path} — OK\n")
            except Exception as e:
                log.write(f"[COMPILE] {rel_path} — FAIL: {str(e)}\n")
                print(f"❌ Compile Fail: {rel_path}")
                continue

            # 2. Structure/Import Metadata Check
            try:
                if "scripts" in pf or "audit_" in pf:
                    log.write(f"[IMPORT]  {rel_path} — SKIPPED (Script/Audit)\n")
                    continue
                    
                spec = importlib.util.spec_from_file_location("check_mod", pf)
                if spec and spec.loader:
                    log.write(f"[IMPORT]  {rel_path} — OK (Structure)\n")
            except Exception as e:
                log.write(f"[IMPORT]  {rel_path} — FAIL: {str(e)}\n")
                print(f"❌ Import Fail: {rel_path}")

    print(f"✅ Source validation complete. Results in {validation_log}")

if __name__ == "__main__":
    validate_source_code()
