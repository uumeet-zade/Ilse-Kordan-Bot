import asyncio
from brain import generate_response

async def main():
    chat_history = ""
    message = "Well asked her to rank 5 latest PMs, she gave me a bland answer and was wrong. Here’s the ranking of the last five Prime Ministers of Caprica, based on the most recent available data:\n\n1. Adriana Flash (SDA) – Current PM as of August 2026.\n2. Patrick Cutter (Moderate Reform) – Served a second term as PM, nominated in May 2065.\n3. Pepe Rutte (CCD/PP) – Likely served before Patrick Cutter’s second term.\n4. Calixte Edinburgh (ALP) – Former PM, served prior to Pepe Rutte.\n5. Mandy Trottier (SDA) – Former PM, served prior to Calixte Edinburgh."
    response = await generate_response(message, chat_history, False, "Umid (ID: 853004086286745640)", None)
    print("Response:\n" + response)

asyncio.run(main())
