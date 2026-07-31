from app.services.rag_service import rag_service


question = input("Ask a question: ")

answer = rag_service.ask(question)

print("\nAI Answer:")
print(answer)