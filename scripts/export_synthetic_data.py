import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.database import SessionLocal
from app.models import Agent
from app.seed import seed_database


def main():
    seed_database()
    db = SessionLocal()
    try:
        ids = {f"SA-{number}" for number in range(1001, 1037)}
        agents = [agent for agent in db.query(Agent).all() if agent.agent_id in ids]
        records = []
        for agent in agents:
            records.append({key: (value.isoformat() if hasattr(value, "isoformat") else value) for key, value in {
                "agent_id": agent.agent_id, "name": agent.name, "description": agent.description, "owner": agent.owner,
                "status": agent.status, "created_at": agent.created_at, "last_activity": agent.last_activity,
                "tools": agent.tools, "permissions": agent.permissions, "scopes": agent.scopes,
                "data_categories": agent.data_categories, "sensitivity": agent.sensitivity,
                "approval_required": agent.approval_required, "risk_score": agent.risk_score,
                "risk_level": agent.risk_level, "events": agent.events,
            }.items()})
        target = ROOT / "data"
        (target / "synthetic_agents.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        with (target / "synthetic_agents.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
            writer.writeheader()
            for record in records:
                writer.writerow({key: json.dumps(value) if isinstance(value, (list, dict)) else value for key, value in record.items()})
        print(f"Exported {len(records)} seeded synthetic agents to data/synthetic_agents.json and .csv")
    finally:
        db.close()


if __name__ == "__main__":
    main()
