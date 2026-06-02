# pip install langchain langchain-ollama langchain-chroma chromadb
import re
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. LOAD EACH MARKDOWN FILE AS A SEPARATE DOCUMENT
docs_path = Path(__file__).parent / "rag"
documents = []
for md_file in sorted(docs_path.glob("*.md")):
    text = md_file.read_text(encoding="utf-8")
    documents.append(Document(page_content=text, metadata={"source": md_file.name}))

print(f"Loaded {len(documents)} installer knowledge base documents.")

# 2. EMBED & STORE — one doc per failure category for precise retrieval
local_embeddings = OllamaEmbeddings(model="nomic-embed-text")
vector_store = Chroma.from_documents(documents=documents, embedding=local_embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

# 3. LOCAL PHI-3 LLM
# temperature=0 prevents creative guessing of paths / registry keys
local_llm = OllamaLLM(model="phi3", temperature=0)

system_prompt = (
    "You are an automated Windows IT assistant for Smart Installer AI.\n"
    "Analyze the installation failure log using ONLY the provided documentation context.\n"
    "Respond in this exact format:\n\n"
    "Root Cause: <one sentence>\n"
    "Confidence: High | Medium | Low\n"
    "Evidence: <what in the log matched>\n"
    "Recommended Fixes:\n1. ...\n2. ...\n3. ...\n"
    "Verification Commands:\n- <command>\n"
    "Escalation: <when to escalate and to whom>\n\n"
    "If the log does not match any known failure, say so explicitly.\n\n"
    "Documentation Context:\n{context}"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Installation failure log:\n\n{input}"),
])

question_answer_chain = create_stuff_documents_chain(local_llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


def extract_relevant_log_lines(log_text: str, tail: int = 20) -> str:
    """Filter to error/warning/failure lines; fall back to last tail lines."""
    error_pattern = re.compile(
        r"(error|critical|failed|failure|timeout|cancelled|denied|missing|crash|unavailable|exception)",
        re.IGNORECASE,
    )
    lines = log_text.strip().splitlines()
    filtered = [l for l in lines if error_pattern.search(l)]
    relevant = filtered if filtered else lines
    return "\n".join(relevant[-tail:])


# 4. RUN DIAGNOSIS
# Replace mock_failure_log with real Smart Installer AI output
mock_failure_log = """
installationOutcome = Failure
error.code = GUI_INSTALL_INCOMPLETE
exitCode = 0
installationCompleted = false
[monitor] process exited cleanly but target executable not found in install directory
[monitor] registry key HKLM\\SOFTWARE\\TargetApp absent
"""

clean_log = extract_relevant_log_lines(mock_failure_log)
result = rag_chain.invoke({"input": clean_log})

print("\n### PHI-3 INSTALLER DIAGNOSIS: ###\n")
print(result["answer"])
print(f"\n[Retrieved from: {', '.join(d.metadata['source'] for d in result['context'])}]")
