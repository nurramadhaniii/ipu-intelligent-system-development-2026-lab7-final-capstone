"""
Lab 7 Module 2: Deterministic Budget Arithmetic & Bounded Iteration
モジュール 2：確定的予算計算と反復上限制御
"""
from typing import Any, Callable, Dict, List, Optional


def compute_budget_summary(items: List[Dict[str, Any]], budget_limit_yen: int) -> Dict[str, Any]:
    """
    TODO [Task 2.1]: Deterministic Budget Arithmetic (Week 5 Concept)
    Compute the budget in Python (never by the LLM), keeping confirmed and estimated costs apart.
    確定費用と見積費用を分けて、Pythonで予算を計算する。

    - budget_limit_yen must be a non-negative int, otherwise raise ValueError.
    - Each cost_yen must be a whole, non-negative number (not bool, not str), otherwise ValueError.
    - known_total_yen:     sum of items with is_estimate = False
    - estimated_total_yen: sum of items with is_estimate = True
    - projected_total_yen: known + estimated (the budget check uses this figure)
    - remaining_yen = budget_limit_yen - projected_total_yen
    - is_within_budget = projected_total_yen <= budget_limit_yen
    - has_estimates, item_count, items (name, cost_yen, is_estimate for each item)
    """
    # --- STUDENT IMPLEMENTATION START ---
    # bool is a subclass of int in Python, so it is rejected explicitly.
    if isinstance(budget_limit_yen, bool) or not isinstance(budget_limit_yen, int) or budget_limit_yen < 0:
        raise ValueError("budget_limit_yen must be a non-negative integer.")

    known_total = 0
    estimated_total = 0
    clean_items = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} must be an object.")
        cost = item.get("cost_yen")
        # Accept int, or a float with no fraction (e.g. 1000.0); reject bool, str, None, 12.5, negatives.
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise ValueError(f"Item {i}: cost_yen must be a number.")
        if isinstance(cost, float):
            if not cost.is_integer():
                raise ValueError(f"Item {i}: cost_yen must be a whole number of yen.")
            cost = int(cost)
        if cost < 0:
            raise ValueError(f"Item {i}: cost_yen cannot be negative.")

        is_estimate = item.get("is_estimate", False) is True
        if is_estimate:
            estimated_total += cost
        else:
            known_total += cost
        clean_items.append({"name": str(item.get("name", "")), "cost_yen": cost, "is_estimate": is_estimate})

    projected_total = known_total + estimated_total
    return {
        "known_total_yen": known_total,
        "estimated_total_yen": estimated_total,
        "projected_total_yen": projected_total,
        "budget_limit_yen": budget_limit_yen,
        "remaining_yen": budget_limit_yen - projected_total,
        "is_within_budget": projected_total <= budget_limit_yen,
        "has_estimates": estimated_total > 0 or any(it["is_estimate"] for it in clean_items),
        "item_count": len(clean_items),
        "items": clean_items,
    }
    # --- STUDENT IMPLEMENTATION END ---


ReviewFn = Callable[[str, int], bool]


def run_bounded_review(drafts: List[str], max_rounds: int = 3,
                       review_fn: Optional[ReviewFn] = None) -> Dict[str, Any]:
    """
    TODO [Task 2.2]: Bounded Review Iteration Ceiling (Week 6 StateGraph Concept)
    Run a draft -> review loop with a hard ceiling of `max_rounds`.
    レビューは最大 max_rounds 回まで。上限に達したら 'needs_attention'（偽の成功を報告しない）。

    drafts:    successive drafts (draft i is what the writer produces in round i)
    review_fn: review_fn(draft, round_number) -> True if approved.
               Default (None): only the last supplied draft is approved.

    - max_rounds < 1 (or not an int) -> raise ValueError
    - Call review_fn at most max_rounds times, stop at the first approval.
    - Approved     -> status "completed", rounds_executed = that round, final_draft = that draft
    - Not approved -> status "needs_attention", final_draft = last reviewed draft ("" if none), add "reason"
    - Always return rounds_executed, max_rounds, status, final_draft and
      history = [{"round": n, "approved": bool}, ...]
    """
    # --- STUDENT IMPLEMENTATION START ---
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
        raise ValueError("max_rounds must be an integer >= 1.")

    drafts = list(drafts or [])
    if review_fn is None:
        last = len(drafts)  # default reviewer: only the last supplied draft is approved
        review_fn = lambda _draft, rnd: rnd == last

    history = []
    final_draft = ""
    rounds_executed = 0
    # The ceiling lives here, in code: the loop can never run more than max_rounds times.
    for rnd in range(1, min(max_rounds, len(drafts)) + 1):
        draft = drafts[rnd - 1]
        approved = review_fn(draft, rnd) is True
        rounds_executed = rnd
        final_draft = draft
        history.append({"round": rnd, "approved": approved})
        if approved:
            return {"status": "completed", "rounds_executed": rnd, "max_rounds": max_rounds,
                    "final_draft": draft, "history": history}

    reason = ("No drafts were supplied." if not drafts
              else f"No draft was approved within {rounds_executed} round(s) (limit {max_rounds}).")
    return {"status": "needs_attention", "rounds_executed": rounds_executed, "max_rounds": max_rounds,
            "final_draft": final_draft, "history": history, "reason": reason}
    # --- STUDENT IMPLEMENTATION END ---