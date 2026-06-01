# pip install langchain langchain-community langchain-chroma chromadb
import re
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. LOAD EACH MARKDOWN FILE AS A SEPARATE DOCUMENT
docs_path = Path(__file__).parent / "rag_docs"
documents = []
for md_file in sorted(docs_path.glob("*.md")):
    text = md_file.read_text(encoding="utf-8")
    documents.append(Document(page_content=text, metadata={"source": md_file.name}))

print(f"Loaded {len(documents)} knowledge base documents.")

# 2. EMBED & STORE — one doc per error for precise retrieval
local_embeddings = OllamaEmbeddings(model="nomic-embed-text")
vector_store = Chroma.from_documents(documents=documents, embedding=local_embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

# 3. LOCAL PHI-3 LLM
# temperature=0 prevents creative guessing of paths / env vars
local_llm = OllamaLLM(model="phi3", temperature=0)

system_prompt = (
    "You are an automated local Windows IT assistant for Ollama installations.\n"
    "Analyze the user's error log snippet using ONLY the provided documentation context. "
    "Provide clear, numbered, step-by-step instructions to fix the issue on Windows.\n"
    "If the log does not match any known error, say so explicitly.\n\n"
    "Documentation Context:\n{context}"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Here is the error log/issue I encountered:\n\n{input}"),
])

question_answer_chain = create_stuff_documents_chain(local_llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


def extract_relevant_log_lines(log_text: str, tail: int = 20) -> str:
    """Filter to error/warning lines; fall back to last `tail` lines."""
    error_pattern = re.compile(r"(error|critical|failed|warning|exception)", re.IGNORECASE)
    lines = log_text.strip().splitlines()
    filtered = [l for l in lines if error_pattern.search(l)]
    relevant = filtered if filtered else lines
    return "\n".join(relevant[-tail:])


# 4. RUN DIAGNOSIS
# Swap mock_error_log for real contents from %LOCALAPPDATA%\Ollama\server.log
mock_error_log = """
[server] error: look up RDNA2 failed
[server] amdgpu: ROCm v7 initialization failed on device index 0
[server] falling back to standard execution or crashing...
"""

clean_log = extract_relevant_log_lines(mock_error_log)
result = rag_chain.invoke({"input": clean_log})

print("\n### PHI-3 DIAGNOSIS & REPAIR INSTRUCTIONS: ###\n")
print(result["answer"])
print(f"\n[Retrieved from: {', '.join(d.metadata['source'] for d in result['context'])}]")
