import os
from anthropic import AsyncAnthropic
from app.models import Lead

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PF_CONTEXT = """Projects Factory is a global AI Products & Services company.
Products: SaaS AI Agents, Agents as a Service (AaaS), AI-Finance.
Pricing: Starter $299/mo, Growth $799/mo, Enterprise custom.
Key benefits: ready in 30 min, no technical team needed, 24/7 availability."""


async def qualify_lead(lead: Lead, lang: str = "es") -> str:
    lang_instruction = "Respond in Spanish." if lang == "es" else "Respond in English."
    prompt = f"""{lang_instruction}

You are an AI sales assistant for Projects Factory.

Analyze this lead and provide:
1. **Score justification** — explain the {lead.score if lead.score > 0 else "potential"} score considering industry fit, company size, and budget signals
2. **Key insights** — 3 bullet points about this lead's potential
3. **Recommended next action** — one specific, actionable step

Lead information:
- Name: {lead.name}
- Company: {lead.company}
- Industry: {lead.industry}
- Estimated deal value: ${lead.value:,.0f}
- Current stage: {lead.stage}
- Notes: {lead.notes or "None"}

{PF_CONTEXT}

Be concise, specific, and actionable. Maximum 200 words."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


async def suggest_followup(lead: Lead, lang: str = "es") -> str:
    lang_instruction = "Respond in Spanish." if lang == "es" else "Respond in English."
    prompt = f"""{lang_instruction}

You are an AI sales assistant for Projects Factory.

Based on this lead's profile, suggest the best follow-up strategy:

1. **Recommended action** — call, email, or meeting (and why)
2. **Best timing** — when to reach out
3. **Key talking points** — 2-3 specific points for this lead
4. **Potential objection** — most likely pushback and how to handle it

Lead information:
- Name: {lead.name}
- Company: {lead.company}
- Industry: {lead.industry}
- Stage: {lead.stage}
- AI Score: {lead.score}/100
- Notes: {lead.notes or "None"}

{PF_CONTEXT}

Be specific and actionable. Maximum 200 words."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


async def draft_email(lead: Lead, lang: str = "es") -> str:
    lang_instruction = "Write the email in Spanish." if lang == "es" else "Write the email in English."
    prompt = f"""{lang_instruction}

You are an AI sales assistant for Projects Factory.

Draft a personalized sales email for this lead. Requirements:
- Compelling subject line referencing their industry
- Open with something specific to their business context
- Mention 1-2 relevant Projects Factory products for their use case
- Include one specific metric or result (e.g., "78% first-contact resolution")
- Clear CTA: schedule a 15-minute demo
- Professional but conversational tone
- Maximum 150 words in the body

Lead:
- Name: {lead.name}
- Company: {lead.company}
- Industry: {lead.industry}
- Notes: {lead.notes or "None"}

{PF_CONTEXT}

Format exactly as:
Subject: [subject line]

[email body]"""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
