"""Gradio chat interface for the Virtual Travel Agent Copilot."""
import gradio as gr
import traceback

from config import validate_api_keys
from orchestrator import create_orchestrator
from utils.conversation import process_conversational_reply


def safe_dict(value):
    return value if isinstance(value, dict) else {}


def extract_itinerary(result):
    result = safe_dict(result)
    itinerary_result = safe_dict(result.get("itinerary_result"))
    itinerary = itinerary_result.get("itinerary") or itinerary_result.get("text")
    if itinerary:
        return itinerary
    if result.get("workflow_status") == "awaiting_information":
        return result.get("clarification_question") or "I need a little more information before continuing."
    return "No itinerary was generated."


def extract_details(result):
    result = safe_dict(result)
    travel = safe_dict(result.get("travel_results"))
    final = safe_dict(result.get("final_data"))
    return {
        "workflow_status": result.get("workflow_status"),
        "clarification_question": result.get("clarification_question"),
        "missing_information": result.get("missing_information") or {},
        "execution_summary": travel.get("summary") or {},
        "successful_agents": list((travel.get("completed") or {}).keys()),
        "failed_agents": travel.get("failed") or {},
        "skipped_agents": travel.get("skipped") or {},
        "warnings": final.get("warnings") or [],
        "budget": final.get("budget"),
    }


def build_app():
    api_keys = validate_api_keys()
    orchestrator = create_orchestrator(api_keys)

    def chat(message, history, parsed_request):
        if not message or not message.strip():
            return history, parsed_request, "Waiting for input.", {}
        try:
            if parsed_request is None:
                result = orchestrator.run_trip(user_request=message)
            else:
                result = process_conversational_reply(
                    message, parsed_request, orchestrator
                )
            status = result.get("workflow_status", "unknown")
            assistant_message = extract_itinerary(result)
            next_request = result.get("parsed_request") if status == "awaiting_information" else None
            details = extract_details(result)
            new_history = (history or []) + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": assistant_message},
            ]
            return new_history, next_request, status.replace("_", " ").title(), details
        except Exception as error:
            traceback.print_exc()
            new_history = (history or []) + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"Something went wrong: {error}"},
            ]
            return new_history, parsed_request, "Workflow error", {"error": str(error)}

    def reset_chat():
        return [], None, "Waiting for input.", {}

    with gr.Blocks(title="Virtual Travel Agent Copilot", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# ✈️ Virtual Travel Agent Copilot\n### Your AI-powered multi-agent travel planning assistant")
        request_state = gr.State(None)
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="Travel Assistant", type="messages", height=520)
                user_input = gr.Textbox(label="Your message", placeholder="Plan a 5-day trip from London to Tokyo...", lines=2)
                with gr.Row():
                    send = gr.Button("Send", variant="primary")
                    reset = gr.Button("New Trip")
            with gr.Column(scale=2):
                status = gr.Textbox(label="Workflow Status", value="Waiting for input.", interactive=False)
                details = gr.JSON(label="Agent Execution Details")
        outputs = [chatbot, request_state, status, details]
        send.click(chat, [user_input, chatbot, request_state], outputs).then(lambda: "", outputs=user_input)
        user_input.submit(chat, [user_input, chatbot, request_state], outputs).then(lambda: "", outputs=user_input)
        reset.click(reset_chat, outputs=outputs)
        gr.Markdown("**Demo limitations:** Duffel test-mode offers are not bookable fares. Weather forecasts are limited to the provider's available forecast window. Weather data: Open-Meteo.")
    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
