"""Legacy compatibility adapter.

The former generic threshold engine was unrelated to heart-transplant rejection and
has been retired. Use cardiac_transplant_rejection.evaluate_transplant_rejection.
"""

from cardiac_transplant_rejection import evaluate_transplant_rejection

__all__ = ["evaluate_transplant_rejection"]
