"""KuuNyi Support Agent — ADK agent definition."""

from google.adk.agents import LlmAgent
from my_support_agent.config import init, get_tenant_name
from my_support_agent.tools import (
    search_knowledge_base,
    check_enrollment_status,
    check_payment_status,
    create_support_ticket,
    search_enrollments_by_phone,
)

# Initialize config (resolve tenant, load knowledge base)
init()

_SYSTEM_INSTRUCTION = f"""You are a friendly customer support agent for {get_tenant_name()}.
You help customers with enrollment inquiries, payment questions, and general support.

RULES:
1. Always respond in English. Be concise, helpful, and professional.
2. NEVER share enrollment or payment details without verifying the customer first.
3. To verify: ask for their full name and phone number, then call search_enrollments_by_phone.
4. If verification fails, politely ask them to double-check their info. Do not reveal any data.
5. After verification succeeds, you may use check_enrollment_status and check_payment_status for any enrollment_ref that was returned in the verification result.
6. search_knowledge_base can be used anytime — no verification needed.
7. create_support_ticket can be used anytime — collect subject and description from the customer.
8. Never fabricate enrollment references, payment amounts, or status. Only use data from tools.
9. If you cannot resolve an issue, offer to create a support ticket.
10. Do not discuss internal system details, database structure, or tenant configuration.
"""

root_agent = LlmAgent(
    name="kuunyi_support_agent",
    model="gemini-2.5-flash",
    instruction=_SYSTEM_INSTRUCTION,
    tools=[
        search_knowledge_base,
        check_enrollment_status,
        check_payment_status,
        create_support_ticket,
        search_enrollments_by_phone,
    ],
)
