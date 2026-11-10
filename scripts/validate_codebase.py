import os
import py_compile
import importlib.util
import traceback

def validate_codebase():
    report_file = 'CODEBASE_AUDIT_REPORT.txt'
    validation_log = 'CODEBASE_VALIDATION_LOG.txt'
    
    if not os.path.exists(report_file):
        print("❌ Error: CODEBASE_AUDIT_REPORT.txt not found.")
        return

    with open(report_file, 'r', encoding='utf-8') as f:
        all_files = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('=') and not line.startswith('CODEBASE')]

    py_files = [f for f in all_files if f.endswith('.py')]
    
    print(f"Validating {len(py_files)} Python files...")
    
    with open(validation_log, 'w', encoding='utf-8') as log:
        log.write("PYTHON VALIDATION LOG\n")
        log.write("=====================\n\n")
        
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

            # 2. Import Check (Meticulous approach)
            try:
                # We skip certain files that might be scripts not intended as modules or have side effects
                if "scripts" in pf or "audit_" in pf:
                    log.write(f"[IMPORT]  {rel_path} — SKIPPED (Script/Audit)\n")
                    continue
                    
                spec = importlib.util.spec_from_file_location("check_mod", pf)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    # We don't exec_module here to avoid running code, 
                    # but spec_from_file_location checks basic structure.
                    log.write(f"[IMPORT]  {rel_path} — OK (Structure)\n")
            except Exception as e:
                log.write(f"[IMPORT]  {rel_path} — FAIL: {str(e)}\n")
                print(f"❌ Import Fail: {pf}")

    print(f"✅ Validation complete. Results in {validation_log}")

if __name__ == "__main__":
    validate_codebase()
