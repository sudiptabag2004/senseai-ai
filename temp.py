import openai
client = openai.OpenAI(
api_key="sk-5xjOFi1j09BA54E5z_OW_A", # Replace with the API key provided to you
base_url="https://agent.dev.hyperverge.org"
)
response = client.chat.completions.create(
model="openai/gpt-4o-mini",
messages=[
{
"role": "user",
"content": "what is 2+2 ?"
}
]
)
print(response)