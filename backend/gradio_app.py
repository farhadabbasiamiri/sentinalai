import os

import gradio as gr
import httpx

API_BASE = os.getenv("SENTINEL_API_URL", "http://127.0.0.1:8000/api")


def call_api(path: str, *, method: str = "GET", json_body: dict | None = None):
    response = httpx.request(method, f"{API_BASE}{path}", json=json_body, timeout=20)
    response.raise_for_status()
    return response.json()


def get_summary():
    try:
        return call_api("/summary")
    except Exception as exc:  # pragma: no cover - demo fallback
        return {"error": str(exc)}


def review_agent(agent_id: str):
    if not agent_id.strip():
        raise gr.Error("Please enter an agent ID such as SA-1002.")
    try:
        payload = {"request": f"Review {agent_id.strip()} and explain its governance risks."}
        result = call_api("/reviews", method="POST", json_body=payload)
        return result
    except Exception as exc:  # pragma: no cover - demo fallback
        return {"error": str(exc)}


def build_dashboard():
    summary = get_summary()
    if "error" in summary:
        return {
            "summary": summary,
            "agent": "",
            "results": {"error": summary["error"]},
        }

    agent_id = "SA-1002"
    try:
        result = review_agent(agent_id)
    except Exception:
        result = {"error": "Unable to review the default agent."}

    return {"summary": summary, "agent": agent_id, "results": result}


with gr.Blocks(title="SentinelAI Governance Demo") as demo:
    gr.Markdown("# SentinelAI Governance Demo\nReview agent governance posture, findings, and approval signals.")

    with gr.Row():
        agent_id = gr.Textbox(label="Agent ID", value="SA-1002", placeholder="SA-1002")
        review_button = gr.Button("Review agent")

    with gr.Row():
        refresh_button = gr.Button("Refresh summary")

    output_summary = gr.JSON(label="Summary")
    output_result = gr.JSON(label="Governance result")

    review_button.click(fn=review_agent, inputs=agent_id, outputs=output_result)
    refresh_button.click(fn=get_summary, inputs=None, outputs=output_summary)

    demo.load(fn=build_dashboard, inputs=None, outputs=[output_summary, agent_id, output_result])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
