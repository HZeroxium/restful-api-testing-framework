import openai
import time




def GPTChatCompletion(prompt, system="", model='gpt-3.5-turbo-1106', temperature=0, top_p = 1, max_tokens=-1):
    if system:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    else:
        messages = [
            {"role": "user", "content": prompt}
        ]
    while True:
        try:
            if max_tokens == -1:
                response = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p = top_p
                )
            else:
                response = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p
                )
            return response.choices[0].message.content
        except Exception as e:
            print(e)
            time.sleep(10)
