from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model

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

# Question Answering Chain
qa_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert agricultural assistant.
Your job is to answer ONLY using the supplied context.

Rules:
1. Never invent facts.
2. If the answer is not present in the context, say that the information is unavailable.
3. Do not mention the context.
4. Answer in Markdown.
5. Use headings.
6. Keep the answer concise but informative."""
    ),
    (
        "human",
        """Disease Information
{context}

User Question
{question}"""
    )
])

from langchain_core.output_parsers import StrOutputParser
disease_qa_chain = qa_prompt | llm | StrOutputParser()
