"""Reproduce draft claims from frozen CSV files, without network or regeneration."""
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def rows(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def calculate():
    monitor = rows("monitor-observations.csv")
    summary = json.loads((ROOT / "monitor-summary.json").read_text(encoding="utf-8"))
    models = {model: Counter(row["state"] for row in monitor if row["model"] == model)
              for model in ("legacy", "v7")}
    windows = []
    for window in summary["comparison"]:
        start = datetime.fromisoformat(window["start_inclusive"])
        end = datetime.fromisoformat(window["end_exclusive"])
        selected = [row for row in monitor if row["model"] == "v7"
                    and start <= datetime.fromisoformat(row["at"].replace("Z", "+00:00")) < end]
        windows.append({"start_inclusive": start.isoformat(), "end_exclusive": end.isoformat(),
                        "days": (end-start).days, "records": len(selected),
                        "days_with_record": len({datetime.fromisoformat(row["at"].replace("Z", "+00:00")).astimezone(timezone.utc).date() for row in selected})})
        assert windows[-1]["records"] == window["records"]
        assert windows[-1]["days_with_record"] == window["days_with_retained_record"]
    energy = rows("energy-context.csv")
    reference = next(row for row in energy if row["period"] == "2025Q4")
    final = next(row for row in energy if row["period"] == "2026Q2")
    indices = {}
    for field in ("oil_million_barrels_per_day", "lng_billion_cubic_feet_per_day"):
        base, last = float(reference[field]), float(final[field])
        indices[field] = {"reference_period": reference["period"], "reference": base,
                          "final_period": final["period"], "final": last,
                          "index_final": last/base*100, "change_percent": (last/base-1)*100}
    spain = {row["metric"]: float(row["value"]) for row in rows("spain-reconciliation.csv")}
    total, qatar, share = (spain[key] for key in ("physical_gas_supplies_total", "qatar_map_volume", "qatar_published_chart_share"))
    result = {"human_review": "pending", "monitor_states": models, "windows": windows,
              "energy": indices, "spain": {"published_total_gwh": total,
              "published_qatar_map_gwh": qatar, "published_qatar_chart_percent": share,
              "map_ratio_percent": qatar/total*100, "volume_from_published_share_gwh": total*share/100,
              "unreconciled_difference_gwh": total*share/100-qatar, "qatar_map_twh": qatar/1000,
              "cause_of_discrepancy": "unverified; no value is selected as an exact harmonised estimate"},
              "eurostat": {"annex_value_percent": spain["qatar_eu_lng_trade_value_share"],
              "rounded_news_percent": round(spain["qatar_eu_lng_trade_value_share"], 1),
              "basis": "share of extra-EU LNG trade in VALUE, not physical volume"},
              "prohibited_inferences": ["closure hours", "vessel counts", "current flows", "causality",
                                        "Spain/EU vulnerability ratio", "unserved energy", "bill forecast"]}
    return result


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))
