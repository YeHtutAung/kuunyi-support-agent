"""Create support ticket tool."""

from google.adk.tools import ToolContext
from my_support_agent.config import get_tenant_id
from my_support_agent.db import get_supabase


_MAX_SUBJECT_LENGTH = 200
_MAX_MESSAGE_LENGTH = 2000
_MAX_TICKETS_PER_SESSION = 3


def create_support_ticket(
    subject: str,
    message: str,
    tool_context: ToolContext,
    phone: str = None,
    enrollment_ref: str = None,
) -> dict:
    """Create a support ticket for issues that need admin attention.

    No identity verification is required. Use this when the customer
    has an issue you cannot resolve directly.

    Args:
        subject: Brief description of the issue
        message: Detailed description of the problem
        phone: Customer's phone number (optional)
        enrollment_ref: Related enrollment reference (optional)
    """
    # Rate limit check
    ticket_count = tool_context.state.get("ticket_count", 0)
    if ticket_count >= _MAX_TICKETS_PER_SESSION:
        return {
            "error": "You've already created the maximum number of support tickets for this session. Please contact support directly for additional issues."
        }

    # Input validation
    if not subject or not subject.strip():
        return {"error": "Please provide a subject for the ticket."}
    if not message or not message.strip():
        return {"error": "Please provide a description of the issue."}

    subject = subject.strip()[:_MAX_SUBJECT_LENGTH]
    message = message.strip()[:_MAX_MESSAGE_LENGTH]

    tenant_id = get_tenant_id()
    supabase = get_supabase()

    ticket_data = {
        "tenant_id": tenant_id,
        "subject": subject,
        "message": message,
    }
    if phone:
        ticket_data["phone"] = phone
    if enrollment_ref:
        ticket_data["enrollment_ref"] = enrollment_ref

    try:
        response = (
            supabase.table("support_tickets")
            .insert(ticket_data)
            .execute()
        )
    except Exception:
        return {"error": "I wasn't able to create a ticket right now. Please contact support directly."}

    if not response.data:
        return {"error": "I wasn't able to create a ticket right now. Please contact support directly."}

    ticket = response.data[0]

    # Increment session counter
    tool_context.state["ticket_count"] = tool_context.state.get("ticket_count", 0) + 1

    return {
        "ticket_id": ticket.get("id"),
        "message": f"Support ticket created successfully. Your ticket ID is {ticket.get('id')}. Our team will review it shortly.",
    }
