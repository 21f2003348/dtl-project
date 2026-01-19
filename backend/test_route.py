"""Quick test script for routing."""
import sys
sys.path.insert(0, r"d:\Animplays\B.E(RVCE)\2nd Year\3rd Sem\DTL\dtl-project\backend")

from services.hybrid_router import get_hybrid_router

router = get_hybrid_router()
result = router.plan_route("Majestic", "RVCE", "bengaluru")

print("=== Majestic to RVCE ===")
print(f"Mode: {result.get('mode')}")
print(f"Time: {result.get('total_time')} min")
print(f"Cost: Rs {result.get('total_cost')}")
print(f"Steps:\n{result.get('steps_text', 'No steps')}")
