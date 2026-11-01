# CCOE CHARUSAT Chatbot - Administrator Guide

This guide explains how to monitor, maintain, and update the Center for Online Education (CCOE) chatbot through the Admin Console (`/admin`).

---

## 1. The Five Administrative Tabs

### Overview
- **Purpose:** A high-level dashboard displaying learner question volume, unanswered rate, response latency, and student feedback.
- **Key Cards:**
  - **Questions:** Total student questions received in the selected window (7, 30, or 90 days).
  - **Unanswered Rate:** Percentage of questions the chatbot could not answer from official course documents.
  - **Median Response Time:** Middle latency for answer generation in seconds.
  - **Positive Feedback:** Helpful versus unhelpful ratings from students. Percentage is shown once 20 ratings accumulate.
  - **Active Users:** Distinct registered accounts asking questions in this period.
- **Chart:** Dual-series daily query trends (Blue: Total questions; Amber: Knowledge gaps).

### Needs Attention
- **Purpose:** Central review hub for questions the chatbot could not answer and answers rated unhelpful.
- **Unanswered questions:** Groups repeated questions with frequency counts, detected programme, and status.
  - Click **Re-test open questions** to check if recently added documents now answer them. Questions passing the relevance threshold are badged as "Probably answerable now".
  - Click **Resolve answerable** to update their status in bulk.
  - Click **Answer this** to add a verified FAQ answer for that question directly into the knowledge base.
- **Answers rated bad:** Reviews negative student feedback with the question asked, assistant answer, and student feedback reason.

### Knowledge Base
- **Purpose:** Catalog of official syllabi, admission criteria, and fee disclosures powering the chatbot.
- **Metrics:** Total vector chunks (target: 301+), source documents, and last ingestion date.
- **Document Table:** Lists each official file with programme breakdown (BBA, BCA, MBA, MCA, General) and chunk count.

### Users
- **Purpose:** Account management and access control for university students and administrators.
- **Actions:**
  - **Make Admin / Demote:** Grant or revoke administrator privileges. You cannot demote your own account.
  - **Disable / Enable:** Block a compromised account from logging in or using the chatbot.
  - **Delete:** Permanently remove an account and its conversation history with typed confirmation.

### System
- **Purpose:** Real-time health monitoring of database connectivity, vector index readiness, AI models, and cache controls.
- **Status Indicators:**
  - **MongoDB:** Green dot confirms database connection and ping response.
  - **Chroma Vector Store:** Green dot confirms vector database is initialized and serving chunks.
  - **Primary & Failover LLM:** Confirms Gemini and Groq API configurations.
- **Cache Management:** View cache hits, misses, and hit rate, or click **Clear question cache** to force fresh lookups.
- **Recent Admin Activity:** Append-only log of the last 50 administrative actions.

---

## 2. Weekly Administrator Routine

Perform these 4 steps once per week (10-15 minutes):

1. **Check the Overview Tab:**
   - Look at the **Unanswered Rate**. If it rises above 15%, review student demand in the Needs Attention tab.
   - Check **Median Response Time**. It should normally remain under 2.5 seconds.
2. **Review Needs Attention:**
   - Sort or filter **Unanswered questions** by frequency.
   - Take the top 3-5 recurring questions. If the information is in an existing document, click **Re-test open questions**. If not, click **Answer this** to draft an official answer.
   - Review **Answers rated bad** and mark resolved items as reviewed.
3. **Verify the Knowledge Base:**
   - When CCOE updates brochures or fee structures on `charusat.online`, upload the new document or confirm the daily synchronization completed successfully.
4. **Inspect System Health:**
   - Confirm all 4 service dots are green.
   - If MongoDB or Chroma is red, check network connectivity and Render service logs.

