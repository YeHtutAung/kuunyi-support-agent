# KuuNyi Smart Customer Support Agent - Setup Guide

## Quick Start

### 1. Prerequisites
- Python 3.9+
- Google Gemini API key (free from https://aistudio.google.com/app/apikey)
- Supabase credentials (get from KuuNyi dev environment)

### 2. Create Project Directory
```bash
mkdir kuunyi-support-agent
cd kuunyi-support-agent

# Create virtual environment
python3 -m venv .venv

# Activate it
# On Mac/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install google-adk supabase python-dotenv
```

### 4. Set Up Environment Variables
Create a `.env` file:
```bash
touch .env
```

Add these to `.env`:
```
# Google Gemini API
GOOGLE_API_KEY=your-gemini-api-key-here

# Supabase (Get from KuuNyi dev dashboard)
SUPABASE_URL=https://fnfvwzwrdsnmwxunciti.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here
```

**How to get Supabase credentials:**
1. Open your KuuNyi dev environment
2. Go to Supabase dashboard → Settings → API
3. Copy the project URL and anon key
4. Paste into `.env`

### 5. Create Agent Folder Structure
```bash
mkdir my_support_agent
touch my_support_agent/__init__.py
touch my_support_agent/agent.py
```

### 6. Copy the Agent Code
Copy the content from `kuunyi_support_agent.py` into `my_support_agent/agent.py`

### 7. Run the Agent
```bash
# Start web UI
adk web

# Then open: http://localhost:8000
```

### 8. Test the Agent
Try these test messages:

**Test 1 - Check Enrollment:**
```
"Can you check my enrollment status? My reference is NM-2026-00042"
```

**Test 2 - Payment Help:**
```
"I'm trying to pay but I'm not sure how"
```

**Test 3 - Search by Phone:**
```
"I don't remember my enrollment reference but my phone is 09-123-456-789"
```

**Test 4 - Create Ticket:**
```
"I think there's a mistake with my payment. My ref is NM-2026-00042 and I paid but it still shows pending"
```

**Test 5 - Knowledge Base:**
```
"What are the JLPT levels?"
```

---

## Tools Included

### 1. **search_knowledge_base(query, tenant_id)**
Searches FAQ and common questions
- Enrollment process
- Payment methods
- Status information
- Refund policy
- Class levels
- Event details

### 2. **check_enrollment_status(enrollment_ref, tenant_id)**
Checks enrollment details:
- Student name and contact info
- Class level and fee
- Enrollment status (pending, confirmed, etc.)
- Payment status
- Enrollment date

### 3. **check_payment_status(enrollment_ref)**
Provides payment details:
- Payment method
- Amount required vs. paid
- Payment status (pending, verified, etc.)
- Bank info if applicable
- Verification status

### 4. **create_support_ticket(subject, message, ...)**
Creates a support ticket:
- Escalates issues to admin
- Links to enrollment if provided
- Stores customer contact info
- Generates ticket ID

### 5. **search_enrollments_by_phone(phone, tenant_id)**
Finds enrollments by phone:
- Searches across all enrollments
- Returns matching records
- Shows status and level for each

---

## How It Works

1. **Customer asks a question**
   - "Where's my order?" → Agent checks status
   - "How do I pay?" → Agent searches knowledge base
   - "I have a problem" → Agent creates ticket

2. **Agent decides which tool to use**
   - Gemini analyzes the question
   - Calls the appropriate tool
   - Gets the result back

3. **Agent formats the response**
   - Makes it easy to read
   - Includes next steps
   - Offers additional help

4. **If agent can't help**
   - Creates a support ticket
   - Escalates to human admin
   - Admin reviews and responds

---

## Database Tables Used

- `enrollments` - Student enrollment records
- `payments` - Payment information
- `classes` - Class/level details
- `tenants` - Organization info
- `users` - Admin/staff users
- `support_tickets` - Support ticket records

---

## Environment Variables Explained

| Variable | What is it? | Where to get |
|----------|-----------|-------------|
| `GOOGLE_API_KEY` | Gemini API key | https://aistudio.google.com/app/apikey |
| `SUPABASE_URL` | Database URL | Supabase dashboard → Settings → API |
| `SUPABASE_KEY` | Database key | Supabase dashboard → Settings → API |

---

## Testing Checklist

- [ ] ADK installed and running
- [ ] `.env` file created with API keys
- [ ] Agent starts with `adk web`
- [ ] Web interface opens at localhost:8000
- [ ] Can check enrollment status
- [ ] Can search knowledge base
- [ ] Can create support ticket
- [ ] Can search by phone number
- [ ] Responses are formatted nicely

---

## Common Issues

### Issue: "SUPABASE_KEY environment variable not set"
**Fix:** Make sure you have `.env` file in project root with `SUPABASE_KEY=...`

### Issue: "Agent not found"
**Fix:** Make sure folder structure is:
```
kuunyi-support-agent/
├── .env
├── my_support_agent/
│   ├── __init__.py
│   └── agent.py
```

### Issue: "Connection refused"
**Fix:** Check that Supabase URL and key are correct in `.env`

### Issue: "No response from agent"
**Fix:** 
1. Check GOOGLE_API_KEY is valid
2. Restart adk web: `adk web`
3. Clear browser cache

---

## Next Steps

1. ✅ Get it running locally
2. Deploy to cloud (Vercel, Cloud Run)
3. Add to your website as chat widget
4. Connect real Telegram/Messenger
5. Add analytics dashboard
6. Monitor support tickets

---

## Deployment to Cloud

### Option A: Vercel (Recommended)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

### Option B: Google Cloud Run
```bash
# Build and deploy
gcloud run deploy kuunyi-support --source .
```

### Option C: Self-hosted
```bash
# Run with Gunicorn
pip install gunicorn
gunicorn my_support_agent:root_agent
```

---

## Support

For issues:
1. Check `.env` file is correct
2. Verify Supabase credentials
3. Check API key is valid
4. Look at ADK documentation: https://google.github.io/adk-docs/

Happy supporting! 🚀
