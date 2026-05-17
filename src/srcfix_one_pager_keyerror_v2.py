from pathlib import Path

TARGET_FILE = Path("src/broker_analytics.py")

text = TARGET_FILE.read_text(encoding="utf-8")

old = '''    latest = brief["premium_evolution"].sort_values("year").tail(1)
'''

new = '''    premium_evolution = brief.get("premium_evolution")

    if (
        premium_evolution is None
        or premium_evolution.empty
        or "year" not in premium_evolution.columns
    ):
        latest = premium_evolution.iloc[0:0] if premium_evolution is not None else __import__("pandas").DataFrame()
    else:
        latest = premium_evolution.sort_values("year").tail(1)
'''

if old not in text:
    raise RuntimeError("Could not find the original premium_evolution sort line to replace.")

text = text.replace(old, new, 1)

TARGET_FILE.write_text(text, encoding="utf-8")

print("Fixed missing 'year' handling in render_one_pager_markdown.")