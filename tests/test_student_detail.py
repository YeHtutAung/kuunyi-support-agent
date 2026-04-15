"""Tests for get_student_detail."""

from unittest.mock import patch
from my_support_agent.tools.student_detail import get_student_detail

STUDENT_RESPONSE = {
    "enrollment_id": "uuid-1",
    "enrollment_ref": "NM-0411-A3X2",
    "student_name_en": "Mg Mg",
    "student_name_mm": "မောင်မောင်",
    "phone": "09123456789",
    "email": "mg@example.com",
    "nrc_number": "12/MAMANA(N)123456",
    "class_level": "N4",
    "intake_name": "April 2026 Intake",
    "status": "confirmed",
    "fee_mmk": 350000,
    "payment": {
        "id": "pay-uuid-1",
        "status": "verified",
        "amount_mmk": 350000,
        "bank_reference": "TXN123",
        "payer_institution": "KBZ",
        "submitted_at": "2026-04-02T08:00:00Z",
        "verified_at": "2026-04-03T09:00:00Z",
        "proof_signed_url": "https://storage.example.com/proof.jpg",
    },
}


def test_calls_correct_endpoint():
    with patch("my_support_agent.tools.student_detail.call_admin_api",
               return_value=STUDENT_RESPONSE) as mock_api:
        get_student_detail("uuid-1")
    mock_api.assert_called_once_with("GET", "/api/admin/students/uuid-1")


def test_returns_student_data():
    with patch("my_support_agent.tools.student_detail.call_admin_api",
               return_value=STUDENT_RESPONSE):
        result = get_student_detail("uuid-1")
    assert result["student_name_en"] == "Mg Mg"
    assert result["payment"]["bank_reference"] == "TXN123"


def test_forwards_api_error():
    with patch("my_support_agent.tools.student_detail.call_admin_api",
               return_value={"error": "Not found."}):
        result = get_student_detail("nonexistent-id")
    assert result == {"error": "Not found."}
