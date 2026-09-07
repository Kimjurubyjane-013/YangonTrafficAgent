"""Manual LLM smoke script; excluded from automated test discovery side effects."""
from agent.llm import ask_llm


request = """
I need the fastest ambulance route
from Hledan Centre to Shwedagon Pagoda.
"""


if __name__ == "__main__":
    print(ask_llm(request))
