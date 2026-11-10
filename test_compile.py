import py_compile
import glob
import sys

def check_compilation():
    print("Checking Python files for syntax errors...")
    files = glob.glob('modules/**/*.py', recursive=True)
    files += glob.glob('AlgoTradingTelegramBotAndFrontend/backend/**/*.py', recursive=True)
    files.extend(['live_options_trader.py', 'main_backtest.py'])
    
    # Exclude virtual environments
    files = [f for f in files if 'venv' not in f and '__pycache__' not in f]
    
    errors = 0
    for f in files:
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"Syntax Error in {f}:\n{e}")
            errors += 1
        except Exception as e:
            print(f"Other Error compiling {f}: {e}")
            errors += 1
            
    if errors == 0:
        print(f"All {len(files)} files compiled successfully.")
    else:
        print(f"Found {errors} compilation errors.")
        sys.exit(1)

if __name__ == '__main__':
    check_compilation()