from anthropic import Anthropic
import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(
    api_key=ANTHROPIC_API_KEY
)

def generate_market_brief(
    regime,
    market_context,
    signals,
    radar_data=None
):

    prompt = f"""
You are the AI strategist for Yuichi AI Terminal.

Current Regime:
{regime}

Market Context:
{market_context}

Signals:
{signals}

Portfolio Impact Radar:
{radar_data}

Rules:

- Maximum 2 sentences
- Under 60 words total
- Mention only the most important development
- Sound like Bloomberg terminal commentary
- No bullet points
- No hype
- No explanations longer than one clause
"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        temperature=0.5,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.content[0].text