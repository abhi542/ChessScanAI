# ChessLensAI: Groq Free Tier Limits & Estimates

The calculations you did previously assumed a massive **5,000 tokens per request**. This would happen if you were sending the *entire* raw PGN or full engine evaluation array to the LLM. 

Because we decoupled the architecture, your actual token usage is microscopically small. We only send the `llm_payload` (stats, opening name, critical mistake, and good move). 

Here is the realistic breakdown based on Groq's Free Tier limits and your actual app architecture.

## 1. The Real Metrics

* **Input Tokens per request:** ~150 - 200 tokens
* **Output Tokens per request (3 sentences):** ~100 tokens
* **Total Tokens per request:** **~300 tokens** (Let's use **500 tokens** to be extremely safe).

### Groq Free Tier Limits (Llama 3 8B / 70B typical limits)
* **RPM (Requests Per Minute):** 30
* **TPM (Tokens Per Minute):** 6,000
* **RPD (Requests Per Day):** 1,000
* **TPD (Tokens Per Day):** 500,000

---

## 2. Resolving the "Minute-Level Bottleneck"

In your previous calculation, 5,000 tokens per request meant you could only process **1 request per minute** before hitting the 6,000 TPM limit. 

With our optimized **500 tokens per request**:
* `6,000 TPM limit / 500 tokens = 12 requests per minute.`
* You can process **12 AI summaries simultaneously every single minute** without any queuing needed. You will never hit this limit during a normal MVP launch.

---

## 3. Daily User Breakdown

Since each request uses roughly 500 tokens, the daily bottleneck is the **1,000 Requests Per Day (RPD)** limit (since 500,000 TPD / 500 = 1,000). 

Here is exactly how many users you can support on the completely **Free Tier** based on user behavior:

| Scenario | Games Reviewed per User / Day | Total Users Supported / Day | Daily Tokens Used (approx) | Limit Hit First |
| :--- | :--- | :--- | :--- | :--- |
| **Heavy Users** | 10 reviews | **100 Users** | 50,000 (10% of limit) | RPD (1,000 limit) |
| **Active Users** | 5 reviews | **200 Users** | 100,000 (20% of limit) | RPD (1,000 limit) |
| **Casual Users** | 2 reviews | **500 Users** | 250,000 (50% of limit) | RPD (1,000 limit) |
| **Light Users** | 1 review | **1,000 Users** | 500,000 (100% of limit) | Both |

---

## 4. Key Takeaways for Production

> [!TIP]
> **You are completely safe for MVP.** 
> Your previous calculation estimated a maximum of 20 users. By restructuring the API to only send the mathematical tallies and the single critical mistake instead of the whole game, you multiplied your app's scalability by **10x**. You can comfortably support **200 to 500 daily active users** entirely on Groq's free tier.

> [!NOTE]
> **What happens if you scale?**
> Even if you go viral and exceed 1,000 reviews per day, Groq's paid tier is roughly **$0.05 per 1 million tokens**. Since your payload is 500 tokens, 1 million tokens equals **2,000 game reviews**. 
> *It will literally cost you 5 cents to process 2,000 AI Coach summaries!*
