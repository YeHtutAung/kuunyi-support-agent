# 🚀 KuuNyi Smart Customer Support Agent - Quick Start

## What You're Building

A **real, production-ready customer support AI agent** that:
- ✅ Checks enrollment status in real-time
- ✅ Verifies payment information
- ✅ Searches knowledge base for answers
- ✅ Creates support tickets automatically
- ✅ Finds enrollments by phone number
- ✅ All integrated with **your real KuuNyi database**

---

## Step 1: Prepare Your Environment (5 minutes)

### 1.1 Get API Keys

**Gemini API Key** (Free):
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy it (starts with `AIza...`)
4. Save it somewhere safe

**Supabase Credentials** (From KuuNyi Dev):
1. Ask your team for KuuNyi dev environment access
2. Open Supabase dashboard
3. Go to Settings → API
4. Copy:
   - Project URL (e.g., `https://fnfvwzwrdsnmwxunciti.supabase.co`)
   - Anon Public Key

---

## Step 2: Set Up Project (10 minutes)

### 2.1 Create Project Folder

```bash
# Create and enter directory
mkdir kuunyi-support-agent
cd kuunyi-support-agent

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Mac/Linux
# OR
.venv\Scripts\activate  # Windows
```

### 2.2 Install Dependencies

```bash
pip install --upgrade pip
pip install google-adk supabase python-dotenv
```

Verify:
```bash
adk --version  # Should show version number
```

### 2.3 Create `.env` File

```bash
touch .env
```

Open `.env` and add:
```
GOOGLE_API_KEY=your-gemini-api-key-here
SUPABASE_URL=https://fnfvwzwrdsnmwxunciti.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here
```

Replace the values with your actual keys!

### 2.4 Create Agent Folder

```bash
mkdir my_support_agent
touch my_support_agent/__init__.py
touch my_support_agent/agent.py
```

Folder structure should now be:
```
kuunyi-support-agent/
├── .env
├── .venv/
├── my_support_agent/
│   ├── __init__.py
│   └── agent.py
└── requirements.txt
```

### 2.5 Copy Agent Code

Copy all the code from `my_support_agent_agent.py` into `my_support_agent/agent.py`

---

## Step 3: Test Your Agent (5 minutes)

### 3.1 Start the Web UI

```bash
adk web
```

You should see:
```
INFO: Application startup complete
+ ─────────────────────────────────────────────────────────────────────────────────+
| ADK Web Server started                                                          |
| For local testing, access at http://localhost:8000.                            |
+ ─────────────────────────────────────────────────────────────────────────────────+
```

### 3.2 Open the Web Interface

Go to: http://localhost:8000

You should see a chat interface!

### 3.3 Test Each Tool

**Test 1: Search Knowledge Base**
```
"What are the JLPT levels?"
```
Expected: Agent explains N5, N4, N3, N2, N1 levels ✓

**Test 2: Check Enrollment**
```
"Can you check my enrollment? Reference is NM-2026-00042"
```
Expected: Agent shows enrollment details, status, fee ✓

**Test 3: Payment Status**
```
"Check payment status for NM-2026-00042"
```
Expected: Agent shows payment details, amount, status ✓

**Test 4: Search by Phone**
```
"Find my enrollment, my phone is 09-123-456-789"
```
Expected: Agent finds enrollments with that phone number ✓

**Test 5: Create Ticket**
```
"I think there's an error with my payment. Ref: NM-2026-00042"
```
Expected: Agent creates a support ticket, gives ticket ID ✓

---

## 🎯 Understanding the Tools

### Tool 1: `search_knowledge_base(query)`
- **What it does**: Searches FAQ for answers
- **When used**: Customer asks general questions
- **Topics**: Enrollment, payment, status, refund, classes, events

### Tool 2: `check_enrollment_status(enrollment_ref)`
- **What it does**: Looks up enrollment in database
- **When used**: Customer wants to know their status
- **Returns**: Name, class, fee, status, payment info

### Tool 3: `check_payment_status(enrollment_ref)`
- **What it does**: Gets payment details
- **When used**: Customer asks about their payment
- **Returns**: Amount, method, status, verification info

### Tool 4: `create_support_ticket(subject, message, ...)`
- **What it does**: Creates support ticket
- **When used**: Agent can't resolve the issue
- **Returns**: Ticket ID, confirmation

### Tool 5: `search_enrollments_by_phone(phone)`
- **What it does**: Finds enrollments by phone number
- **When used**: Customer forgot their enrollment reference
- **Returns**: List of matching enrollments

---

## 📊 How the Agent Thinks

```
Customer: "Can you check my status? I think my payment wasn't received"
    ↓
Agent: "I'll help! Let me check your enrollment and payment status"
    ↓
Agent calls: check_enrollment_status("NM-2026-00042")
Agent calls: check_payment_status("NM-2026-00042")
    ↓
Agent sees: enrollment confirmed, payment pending
    ↓
Agent: "Your enrollment is confirmed! But your payment is still pending. 
        Let me create a support ticket so admin can check the bank transfer"
    ↓
Agent calls: create_support_ticket(...)
    ↓
Customer: "Thank you! You created ticket #XYZ123. We'll help!"
```

---

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'google'"
**Fix**: Make sure virtual environment is activated
```bash
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate      # Windows
```

### Issue: "SUPABASE_KEY environment variable not set"
**Fix**: Check `.env` file exists and has the correct key
```bash
cat .env  # Linux/Mac
type .env  # Windows
```

### Issue: "Agent not responding"
**Fix**: 
1. Check GOOGLE_API_KEY is correct
2. Verify Supabase URL and key match your database
3. Restart adk web: `adk web`

### Issue: "Connection to Supabase failed"
**Fix**:
1. Verify SUPABASE_URL is correct
2. Verify SUPABASE_KEY is correct (not service_role key)
3. Check your internet connection

---

## 📈 Next Steps

### Option A: Expand Locally (Today)
- [ ] Add more tools (notify customer, check refund status, etc.)
- [ ] Test with real KuuNyi data
- [ ] Add analytics dashboard

### Option B: Deploy to Cloud (This Week)
- [ ] Deploy to Vercel / Google Cloud Run
- [ ] Add chat widget to your website
- [ ] Monitor support tickets

### Option C: Advanced Features (Next Week)
- [ ] Connect Telegram bot
- [ ] Add email notifications
- [ ] Create admin dashboard
- [ ] Add multi-language support

---

## 📚 Learning Resources

- **ADK Documentation**: https://google.github.io/adk-docs/
- **Supabase Guide**: https://supabase.com/docs
- **Gemini API**: https://ai.google.dev/
- **Your KuuNyi Analysis**: See KuuNyi_Analysis.md

---

## 🎓 How It All Works Together

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOMER SUPPORT FLOW                    │
└─────────────────────────────────────────────────────────────┘

Customer
   ↓
[Chat Interface - localhost:8000]
   ↓
[ADK Agent - Gemini LLM]
   ├→ Analyzes question
   ├→ Decides which tool(s) to use
   ├→ Calls the tools
   └→ Formats response
   ↓
[Tools - Python Functions]
   ├→ search_knowledge_base()
   ├→ check_enrollment_status()
   ├→ check_payment_status()
   ├→ create_support_ticket()
   └→ search_enrollments_by_phone()
   ↓
[KuuNyi Database - Supabase PostgreSQL]
   ├→ enrollments table
   ├→ payments table
   ├→ classes table
   ├→ tenants table
   └→ support_tickets table
   ↓
Response back to Customer
```

---

## ✅ Success Checklist

- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install ...`)
- [ ] `.env` file created with API keys
- [ ] Agent folder created (`my_support_agent/`)
- [ ] `agent.py` copied with all tools
- [ ] `adk web` starts without errors
- [ ] Web interface opens at localhost:8000
- [ ] Can search knowledge base
- [ ] Can check enrollment status
- [ ] Can check payment status
- [ ] Can create support ticket
- [ ] Can search by phone number

---

## 🚀 You're Ready!

Once everything works locally, you have:

✅ A working AI support agent
✅ Connected to real KuuNyi data
✅ Using real Gemini LLM
✅ With 5 powerful tools
✅ Ready to deploy anywhere

**Next**: Share the `.env` setup details with your team, deploy to cloud, and put it on your website! 🎉

---

## Questions?

1. Check the KUUNYI_SETUP.md for detailed setup
2. Review the kuunyi_support_agent.py for code details
3. Check ADK docs: https://google.github.io/adk-docs/
4. Ask me for help!

Happy supporting! 💪
