# backend/app/ai_engine.py
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# --- ADDITIONS FOR SYMPTOM CHECKER ---

# In a real-world app, this would be in a database or a proper session manager.
# For our hackathon prototype, a simple dictionary is enough to track conversations.
user_sessions = {} 

SYMPTOM_QUESTIONS = [
    {"key": "fever", "question": "First, do you have a fever? (yes/no)"},
    {"key": "cough", "question": "Do you have a cough? (yes/no)"},
    {"key": "headache", "question": "Do you have a headache? (yes/no)"},
    {"key": "rash", "question": "Finally, do you have a skin rash? (yes/no)"},
]

# --- END ADDITIONS ---

load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

qa_chain = None

def initialize_ai_engine():
    global qa_chain
    if qa_chain is not None:
        print("AI Engine is already initialized.")
        return

    try:
        print("Initializing AI Engine...")

        # --- FIX 1 & 2: Update model name and remove deprecated argument ---
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.3)
        # --- END FIX 1 & 2 ---

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        knowledge_base_path = os.path.join(backend_dir, "knowledge_base.txt")
        print(f"Loading knowledge base from: {knowledge_base_path}")
        loader = TextLoader(file_path=knowledge_base_path, encoding="utf-8")
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        vector_store = Chroma.from_documents(texts, embeddings)
        prompt_template = """
        You are Vaidya Dhara, a helpful and respectful public health assistant.
        Your goal is to provide clear and accurate health information based ONLY on the context provided.
        Do not answer any questions outside of the given context.
        If the user asks for a medical diagnosis, or asks a question you cannot answer from the context,
        politely refuse and advise them to consult a qualified medical professional.
        Never invent information.

        CONTEXT:
        {context}

        QUESTION:
        {question}

        ANSWER:
        """
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(),
            chain_type_kwargs={"prompt": PROMPT},
            return_source_documents=False
        )
        print("AI Engine initialized successfully.")
    except Exception as e:
        print(f"Error initializing AI Engine: {e}")
        raise

# REPLACE the old get_ai_response function with this new one

def get_ai_response(query: str, session_id: str = "default_user") -> str:
    """
    Gets a response from the AI engine. It now handles the symptom checker
    state or defaults to the LangChain RAG pipeline.
    """

    # Check if the user is currently in a symptom checker session
    if session_id in user_sessions:
        session = user_sessions[session_id]

        # Record the user's answer (yes/no)
        last_question_key = SYMPTOM_QUESTIONS[session['question_index']]['key']
        session['answers'][last_question_key] = "yes" if "yes" in query.lower() else "no"

        # Move to the next question
        session['question_index'] += 1

        # If there are more questions, ask the next one
        if session['question_index'] < len(SYMPTOM_QUESTIONS):
            return SYMPTOM_QUESTIONS[session['question_index']]['question']
        else:
            # If all questions are answered, provide a summary
            answers = session['answers']
            symptoms_present = [key for key, value in answers.items() if value == "yes"]

            # Clean up the session
            del user_sessions[session_id]

            if not symptoms_present:
                return "Based on your answers, you haven't reported any of the key symptoms. However, if you feel unwell, please consult a doctor."

            summary = f"Thank you. You've indicated the following symptoms: {', '.join(symptoms_present)}. "

            # Simple logic for providing guidance
            if "fever" in symptoms_present and "rash" in symptoms_present:
                summary += "Fever combined with a rash can be an indicator of conditions like Dengue. "
            elif "fever" in symptoms_present and "cough" in symptoms_present:
                summary += "Fever and cough are common symptoms for many respiratory illnesses, including TB. "

            summary += "This is not a diagnosis. Please consult a medical professional for accurate advice."
            return summary

    # If not in a session, check if the user wants to start one
    if "symptom" in query.lower() or "check" in query.lower():
        # Start a new session for the user
        user_sessions[session_id] = {
            "question_index": 0,
            "answers": {}
        }
        # Ask the first question
        return SYMPTOM_QUESTIONS[0]['question']

    # If none of the above, use the default LangChain RAG Q&A
    if qa_chain is None:
        return "Sorry, the AI engine is not available at the moment. Please try again later."

    try:
        result = qa_chain.invoke({"query": query})
        return result.get("result", "I could not find an answer in my knowledge base.")
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return "Sorry, an error occurred while processing your request."