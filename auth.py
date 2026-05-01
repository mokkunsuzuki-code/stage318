from db import get_plan_by_api_key


def is_valid_key(api_key):
    if not api_key:
        return False

    return get_plan_by_api_key(api_key) is not None


def get_plan(api_key):
    plan = get_plan_by_api_key(api_key)

    if not plan:
        return "free"

    return plan
