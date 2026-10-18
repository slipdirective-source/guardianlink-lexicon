"""Run the full prototype battery. Exit 0 iff everything passes."""
import sys
import traceback

sys.path.insert(0, "/home/hatch/workspace/gl-integration/prototype")

from tests import test_battery, test_composition, test_adversarial, test_feedback, test_sacrifice, test_recovery

MODULES = [test_battery, test_composition, test_adversarial, test_feedback, test_sacrifice, test_recovery]

passed, failed = 0, []
for mod in MODULES:
    for fn in mod.TESTS:
        try:
            msg = fn()
            passed += 1
            print(f"  PASS  {msg}")
        except Exception as e:
            failed.append((fn.__name__, e))
            print(f"  FAIL  {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc(limit=3)

print(f"\n{passed} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
