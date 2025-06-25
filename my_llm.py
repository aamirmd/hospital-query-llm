from huggingface_hub import InferenceClient

# Model
llm_agent = "microsoft/Phi-3-mini-4k-instruct"

# Read API key
api_key_filename = "hf_api_key.txt"
with open(api_key_filename, "r") as f:
    api_key = f.read()

# Generates LLM response using a prompt (user input) and model name
def llm_prompt(prompt, model):

    # Define inference client
    client = InferenceClient(
        provider="hf-inference",
        api_key=api_key,
    )

    # Get response from LLM
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=50
    )

    # Return response
    return completion.choices[0].message




user_input = ""

# Prompt the user until they exit
while user_input != "exit":
    user_input = input("Enter a prompt: ")
    if user_input == "exit":
        break
    print(llm_prompt(user_input, llm_agent))



print("--End of session--")