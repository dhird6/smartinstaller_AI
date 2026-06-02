import ollama
response = ollama.generate(model='phi3', prompt="What is the capital of France?")
print(response)