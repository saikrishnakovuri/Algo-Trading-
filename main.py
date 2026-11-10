import os
from orchestrator import Orchestrator


def main():
    print("Running orchestrator cycle (demo/dry-run)")
    orch = Orchestrator()
    decision = orch.run_cycle(dry_run=True)
    print("\n" + "=" * 40)
    print("AI TRADING DECISION")
    print("=" * 40)
    print(decision)
    print("=" * 40)


if __name__ == "__main__":
    main()
