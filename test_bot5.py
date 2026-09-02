import asyncio
from brain import generate_response

async def main():
    chat_history = ""
    message = "Who were the last 5 Prime Ministers? Only give me the list."
    response = await generate_response(message, chat_history, False, "Umid (ID: 853004086286745640)", None)
    print("Response:\n" + response)

asyncio.run(main())
