# Before running:
# pip install azure-ai-projects>=2.1.0 azure-identity

import os
import json
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ResponseStreamEventType

endpoint = "https://roshinit2411-4768-resource.services.ai.azure.com/api/projects/roshinit2411-4768"

def run_reconciliation(payload_key="inv_102_discrepancy"):
    # 1. Load the benchmark payload
    with open("test_payloads.json", "r") as f:
        payloads = json.load(f)
    
    invoice_data = payloads[payload_key]
    formatted_input = json.dumps(invoice_data, indent=2)

    print(f"\n=======================================================")
    print(f"Starting VendorGuard Workflow for: {payload_key}")
    print(f"Invoice: {invoice_data['invoice_number']} | Vendor: {invoice_data['vendor_name']}")
    print(f"=======================================================\n")

    # 2. Connect to Azure AI Project Client
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    with project_client:
        workflow = {
            "name": "vendorguard-workflow",
            "version": "1",
        }
        
        openai_client = project_client.get_openai_client()

        # 3. Create conversation session
        conversation = openai_client.conversations.create()
        print(f"Created conversation session (ID: {conversation.id})")

        # 4. Stream response from the workflow
        stream = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": workflow["name"], "type": "agent_reference"}},
            input=formatted_input,
            stream=True,
            metadata={"x-ms-debug-mode-enabled": "1"},
        )

        for event in stream:
            if event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DONE:
                print("\n[Audit Decision]:\n", event.text)
            elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_ADDED and getattr(event.item, 'type', None) == "workflow_action":
                print(f"\n>>> Executing Node: '{event.item.action_id}'")
            elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_DONE and getattr(event.item, 'type', None) == "workflow_action":
                print(f"<<< Completed Node: '{event.item.action_id}' (Status: {event.item.status})")
            elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DELTA:
                print(event.delta, end="", flush=True)

        # 5. Clean up session
        openai_client.conversations.delete(conversation_id=conversation.id)
        print("\n\nConversation cleaned up.")

if __name__ == "__main__":
    # Test discrepancy scenario ($1,600 overbill -> STAGE_DISPUTE_HITL)
    run_reconciliation("inv_102_discrepancy")