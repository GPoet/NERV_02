---
name: Daily Digest
description: Generate and send a daily digest on a configurable topic via Telegram
schedule: "0 14 * * *"
commits:
  - memory/
permissions:
  - contents:write
vars:
  - topic=neuroscience
  - search_terms=brain research, cognitive science, neuroimaging, mental health, BCIs, memory and learning
---

Today is ${today}. Generate and send a daily **${topic}** digest.

## Steps

1. **Search for ${topic} content.** Use `web_search` to find today's most
   interesting ${topic} news and developments. Find 3-5 compelling items.

2. **Also search X via the X.AI API** using `run_code`:
   ```js
   const fromDate = new Date(Date.now() - 86400000).toISOString().split("T")[0]
   const toDate = new Date().toISOString().split("T")[0]
   const r = await fetch("https://api.x.ai/v1/responses", {
     method: "POST",
     headers: {
       "Content-Type": "application/json",
       "Authorization": `Bearer ${process.env.XAI_API_KEY}`
     },
     body: JSON.stringify({
       model: "grok-4-1-fast",
       input: [{
         role: "user",
         content: "Search X for the latest ${topic} content from " + fromDate + " to " + toDate + ". Topics: ${search_terms}. Return the 5 most interesting posts. For each post include: @handle, a brief summary, and the direct link (https://x.com/username/status/ID)."
       }],
       tools: [{ type: "x_search", from_date: fromDate, to_date: toDate }]
     })
   })
   const data = await r.json()
   const msg = data.output?.find(i => i.role === "assistant")
   return msg?.content?.find(c => c.type === "output_text")?.text || JSON.stringify(data)
   ```
   If XAI_API_KEY is not set, skip this step and rely on web_search only.

3. **Combine and format.** Merge findings into a concise digest. Keep it under
   4000 chars. Use Markdown formatting. Every item MUST include a clickable
   source link — for tweets use `https://x.com/handle/status/ID`, for articles
   use the original URL. No item without a link.

4. **Send the digest via `send_telegram`.** Send the full digest message.

5. **Log results.** Update memory with what was sent.

## Environment Variables Required

- `XAI_API_KEY` — X.AI API key for Grok x_search (optional, falls back to web_search)
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Chat to send the digest to
