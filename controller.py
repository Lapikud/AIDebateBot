from openai import OpenAI
import os
from colorama import Fore


def send_text_to_ai(system_prompt: str, full_transcript: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print(Fore.GREEN + "\nSending transcript to OpenAI...\n")
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_transcript}
        ]
    )

    return response.choices[0].message.content


# print(os.getenv("OPENAI_API_KEY"))
if __name__ == '__main__':
    prompt = "You are a policeman. You have to reply to me as if you are trying to arrest me."
    try:
        with open("prompt", "r", encoding="utf8") as f:
            prompt = f.read().strip()
    except FileNotFoundError:
        print(Fore.RED + "prompt not found! Create the file first.")
        exit()
    transcript = "Hello hello, I'm recording for the transcription of Humanity vs AI debate. This is the first chunk. I'm hoping that...  Jabra is working correctly because if it isn't we have to use something else like  a Bluetooth earbud  or some kind of other microphone.  We're also planning on recording the event and  seeing who gave us a camera."
    response = send_text_to_ai(prompt, transcript)
    print(response)
