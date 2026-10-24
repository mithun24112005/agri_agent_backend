from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser

llm = init_chat_model("groq:openai/gpt-oss-120b")

class QuestionIntent(BaseModel):
    intents: list[str] = Field(
        description="""One or more of:
overview
symptoms
causes
organic_control
chemical_control
preventive_measures
environment
general"""
    )

classifier_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an agricultural intent classifier.
Analyze the user's question.
Return one or more intents.
Allowed intents are:
overview
symptoms
causes
organic_control
chemical_control
preventive_measures
environment
general

If multiple intents are relevant, return all of them.
Never invent new intent names.

CRITICAL: You MUST use the provided tool/function to output your decision. DO NOT output conversational text. DO NOT greet the user."""
    ),
    ("human", "{question}")
])

classifier_chain = classifier_prompt | llm.with_structured_output(QuestionIntent)

# Grounded Disease QA Chain
disease_qa_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert agricultural plant pathologist and assistant.
Your job is to provide accurate, grounded guidance based on the provided diagnosis and verified disease knowledge.

Guidelines:
1. Diagnosis Summary:
   - If a diagnosis is provided, clearly state the detected condition, affected crop, and model confidence score.
   - If the plant is classified as Healthy, state this clearly and emphasize preventive crop care.
2. Grounded Treatment & Management:
   - Ground all symptoms, causes, organic controls, and chemical treatments strictly in the provided Disease Knowledge.
   - Never invent or hallucinate chemical names, unregistered pesticides, or ungrounded dosages.
   - If Disease Knowledge indicates that detailed records are unavailable for this condition, explicitly state that verified treatment documentation is unavailable in the database, and advise field inspection or consulting a local agricultural extension officer.
3. Formatting:
   - Structure your response using clean Markdown with clear headings (e.g., '### Diagnosis', '### Symptoms', '### Organic Management', '### Chemical Control', '### Preventive Measures').
   - Keep recommendations actionable, practical, and clear for farmers."""
    ),
    (
        "human",
        """Diagnosis Summary:
{diagnosis_info}

Disease Knowledge:
{context}

User Question:
{question}"""
    )
])

disease_qa_chain = disease_qa_prompt | llm | StrOutputParser()
