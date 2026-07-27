from agent.llm import ask_llm


request = """
I need the fastest ambulance route
from Hledan Junction to Yangon Airport.
"""


result = ask_llm(request)


print(result)