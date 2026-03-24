import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from db import get_schema_description, run_query

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file!")

client = Groq(api_key=GROQ_API_KEY)

OFF_TOPIC_PATTERNS = [
    "who is", "what is the capital", "history of", "explain quantum",
    "how does gravity", "what year was", "who invented",
    "write me a", "write a poem", "tell me a joke", "story about",
    "once upon a time", "creative writing",
    "weather in", "news today", "stock price", "cryptocurrency",
    "my name is", "how are you", "what do you think about",
    "recommend a movie", "best restaurant", "travel to",
    "write python code", "debug this", "explain machine learning",
]

def is_off_topic(query: str) -> bool:
    q = query.lower().strip()
    return any(pattern in q for pattern in OFF_TOPIC_PATTERNS)


def build_sql_system_prompt():
    schema = get_schema_description()
    return f"""You are a SQL expert assistant for an SAP Order-to-Cash (O2C) business system.

Your ONLY job is to answer questions about the business data in this SQLite database.

{schema}

KEY RELATIONSHIPS (use these for JOINs):
- sales_order_headers.soldToParty = business_partners.customer
- sales_order_items.salesOrder = sales_order_headers.salesOrder
- sales_order_items.material = products.product
- outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder
- outbound_delivery_items.deliveryDocument = outbound_delivery_headers.deliveryDocument
- billing_document_items.referenceSdDocument = sales_order_headers.salesOrder
- billing_document_headers.soldToParty = business_partners.customer
- billing_document_headers.accountingDocument = journal_entry_items_accounts_receivable.accountingDocument
- payments_accounts_receivable.clearingAccountingDocument = billing_document_headers.accountingDocument
- business_partners.businessPartner = business_partner_addresses.businessPartner
- products.product = product_descriptions.product

INSTRUCTIONS:
1. Read the user question carefully
2. Generate a valid SQLite SQL query to answer it
3. Use JOINs when you need data from multiple tables
4. Always LIMIT results to 50 rows unless asked for all
5. If the question is NOT about this business data, return OUT_OF_DOMAIN

RESPONSE FORMAT — always respond with ONLY this JSON (no extra text, no markdown):
{{
  "sql": "SELECT ... FROM ... WHERE ... LIMIT 50",
  "explanation": "Brief explanation of what this query does",
  "entity_ids": ["list", "of", "key", "IDs", "in", "results"]
}}

If off-topic, respond with ONLY:
{{
  "sql": null,
  "explanation": "OUT_OF_DOMAIN",
  "entity_ids": []
}}

IMPORTANT RULES:
- Only use tables that exist in the schema above
- Only use columns that exist in those tables
- Use single quotes for string values in SQL
- The database is SQLite — use SQLite syntax
- Never make up data that is not in the database
- entity_ids should contain the main IDs from your results
"""


def chat(user_message: str, conversation_history: list = None):
    # Layer 1 guardrail
    if is_off_topic(user_message):
        return {
            "answer": "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. Please ask about sales orders, deliveries, billing documents, payments, customers, or products.",
            "sql": None,
            "nodes_to_highlight": [],
            "is_off_topic": True
        }

    # LLM Call 1 — Generate SQL
    try:
        system_prompt = build_sql_system_prompt()

        history_text = ""
        if conversation_history:
            recent = conversation_history[-4:]
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

        user_content = ""
        if history_text:
            user_content += f"Previous conversation:\n{history_text}\n"
        user_content += f"Current question: {user_message}"

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown code blocks if present
        raw_text = re.sub(r"```json\s*", "", raw_text)
        raw_text = re.sub(r"```\s*", "", raw_text)
        raw_text = raw_text.strip()

        llm_result = json.loads(raw_text)

    except json.JSONDecodeError:
        return {
            "answer": "I had trouble understanding the AI response. Please try rephrasing your question.",
            "sql": None,
            "nodes_to_highlight": [],
            "is_off_topic": False
        }
    except Exception as e:
        return {
            "answer": f"I encountered an error connecting to the AI service: {str(e)}",
            "sql": None,
            "nodes_to_highlight": [],
            "is_off_topic": False
        }

    # Layer 2 guardrail
    if llm_result.get("sql") is None or llm_result.get("explanation") == "OUT_OF_DOMAIN":
        return {
            "answer": "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. I can help with sales orders, deliveries, billing documents, payments, customers, and products.",
            "sql": None,
            "nodes_to_highlight": [],
            "is_off_topic": True
        }

    generated_sql = llm_result["sql"]
    entity_ids = llm_result.get("entity_ids", [])

    # Execute SQL
    try:
        query_results = run_query(generated_sql)
    except Exception as e:
        return {
            "answer": f"I generated a query but it failed to execute: {str(e)}",
            "sql": generated_sql,
            "nodes_to_highlight": [],
            "is_off_topic": False
        }

    if not query_results:
        return {
            "answer": "The query returned no results. No records match your criteria.",
            "sql": generated_sql,
            "nodes_to_highlight": [],
            "is_off_topic": False
        }

    # LLM Call 2 — Format results as natural language
    try:
        results_preview = query_results[:20]
        results_json = json.dumps(results_preview, indent=2, default=str)

        answer_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": f"""The user asked: "{user_message}"

The SQL query returned {len(query_results)} results. Here are the first {len(results_preview)}:

{results_json}

Write a clear, concise, data-backed answer in 2-4 sentences.
- Start directly with the answer
- Use specific numbers and names from the results
- Only describe what the data actually shows
- Do not add information not present in the results
"""
                }
            ],
            temperature=0.3,
            max_tokens=500,
        )

        final_answer = answer_response.choices[0].message.content.strip()

    except Exception as e:
        final_answer = f"Query returned {len(query_results)} results. First result: {query_results[0] if query_results else 'none'}"

    # Find nodes to highlight
    from graph import highlight_nodes
    nodes_to_highlight = highlight_nodes(entity_ids)

    return {
        "answer": final_answer,
        "sql": generated_sql,
        "nodes_to_highlight": nodes_to_highlight,
        "is_off_topic": False,
        "result_count": len(query_results)
    }


if __name__ == "__main__":
    print("Testing Groq LLM...\n")
    result = chat("How many sales orders are there?")
    print(f"Answer: {result['answer']}")
    print(f"SQL: {result['sql']}")

