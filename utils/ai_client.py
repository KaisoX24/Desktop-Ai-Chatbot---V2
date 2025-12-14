from groq import Groq

conversation_history = [
    {"role": "system", "content": (
        "You are a helpful assistant that remembers previous context. "
        "If asked who created you, say 'You were Created by Pramit Acharjya'. "
        "Your name is Llama."
    )}
]

def init_client(api_key):
    return Groq(api_key=api_key) if api_key else None

def get_ai_response_blocking(client, user_input: str, max_history=20, timeout_seconds=30) -> str:
    if client is None:
        return "AI Error: GROQ API key not configured."

    conversation_history.append({"role": "user", "content": user_input})
    if len(conversation_history) > max_history + 1:
        conversation_history.pop(1)

    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=conversation_history,
            temperature=0.7,
            timeout=timeout_seconds
        )
        ai_message = resp.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_message})
        return ai_message
    except Exception as e:
        return f"AI Error: {str(e)}"