# Graph-Based Data Modeling and Query System

## Overview
This project is a graph-based business intelligence system built on top of a multi-entity Order-to-Cash style dataset. The goal of the system is to unify fragmented business records such as sales orders, deliveries, billing documents, payments, customers, and products into a connected graph that can be explored visually and queried using natural language.

The application combines:
- a graph representation of business entities and relationships
- a graph visualization interface
- a conversational query interface powered by an LLM
- a structured query layer over the underlying dataset

The system is designed to answer only dataset-grounded questions and reject unrelated prompts.
## Links
- Live Demo: [To be added after deployment]
- GitHub Repository: https://github.com/gopi-28/graph-query-system
---

## What the System Does
The system supports the following workflow:
1. Ingest structured business data from the dataset
2. Load the data into a relational database
3. Construct an in-memory graph of interconnected entities
4. Visualize the graph in a web interface
5. Accept natural language questions from the user
6. Translate the question into a structured query
7. Execute the query against the dataset
8. Return a grounded natural language response

This is not a static Q&A system. Responses are generated only after querying the data.

---

## Architecture
The project is split into two main parts:

### Backend
The backend is built with **FastAPI** and is responsible for:
- loading and normalizing the dataset
- storing data in SQLite
- constructing the graph using NetworkX
- exposing APIs for graph exploration
- handling natural language queries through the LLM workflow

Main backend components:
- `db.py` — loads dataset files into SQLite
- `graph.py` — constructs the graph and graph expansion logic
- `llm.py` — prompt design, NL-to-SQL flow, answer generation, and guardrails
- `main.py` — FastAPI application and API routes

### Frontend
The frontend is built with **React (Vite)** and is responsible for:
- rendering the graph
- showing node metadata
- allowing node expansion
- providing a chat interface for natural language questions
- highlighting graph nodes related to query results

Main frontend components:
- `App.jsx` — layout and orchestration
- `GraphView.jsx` — graph visualization with Cytoscape.js
- `ChatPanel.jsx` — chat interface and query interaction

---

## Database / Storage Choice
I used **SQLite** as the primary storage layer.

### Why SQLite
- lightweight and easy to set up
- no external database server required
- works well for local development and demos
- supports SQL querying cleanly for LLM-generated structured queries
- suitable for the size of the provided dataset

### Tradeoff
SQLite is not ideal for highly concurrent or very large-scale production systems, but it is a strong choice here because the assignment prioritizes clarity, speed of setup, and reasoning over infrastructure complexity.

### Graph Storage
I used **NetworkX** as the graph layer.

### Why NetworkX
- easy to construct and manipulate entity relationships
- flexible for modelling custom nodes and edges
- ideal for in-memory graph traversal and neighborhood expansion
- avoids the complexity of introducing a dedicated graph database for this assignment

### Tradeoff
NetworkX is not a persistent graph database. In this project, the graph is derived from the relational dataset and rebuilt in memory when needed. This keeps the architecture simple and easy to explain.

---

## Graph Modelling
The dataset contains multiple related business entities. I modelled the system as a graph where:

### Nodes
Nodes represent business entities such as:
- Customer
- SalesOrder
- SalesOrderItem
- Delivery
- BillingDocument
- JournalEntry
- Payment
- Product
- Address

### Edges
Edges represent relationships between those entities, such as:
- Customer → SalesOrder
- SalesOrder → SalesOrderItem
- SalesOrderItem → Product
- SalesOrder → Delivery
- Delivery → BillingDocument
- BillingDocument → JournalEntry
- JournalEntry → Payment
- Customer → Address

This graph structure makes it possible to trace end-to-end business flows and inspect missing or broken relationships.

---

## Graph Visualization
The graph visualization is implemented using **Cytoscape.js** in the React frontend.

The interface supports:
- viewing nodes and edges
- clicking nodes to inspect metadata
- expanding nodes to view connected neighbors
- highlighting relevant nodes returned from chat queries

The UI is intentionally simple and focused on usability over visual complexity, in line with the task requirements.

---

## LLM Integration and Prompting Strategy
The conversational query interface is designed around a grounded two-step workflow:

### Step 1 — Natural Language to Structured Query
The LLM receives:
- the user’s natural language question
- the database schema
- domain instructions
- output formatting instructions

The LLM generates a structured SQL query only if the question is relevant to the dataset.

### Step 2 — Structured Results to Natural Language Answer
The generated SQL query is executed against SQLite.
The returned rows are then passed back to the LLM, which produces a concise natural language answer based only on the query results.

### Why this approach
This design keeps answers grounded in the dataset instead of allowing unconstrained free-form generation.
It also makes the reasoning process more transparent and debuggable because the generated SQL can be inspected directly.

### Prompting Principles Used
- explicitly provide schema context
- instruct the model to stay within the dataset
- require structured output for SQL generation
- reject out-of-domain requests
- generate answers only from query results

---

## Guardrails
Guardrails are an important part of the system.

The system is restricted to the provided business dataset and rejects unrelated prompts.

### Guardrail Approach
1. **Pre-check / domain filtering**
   - obvious off-topic prompts are identified early
   - examples: jokes, poems, general knowledge, unrelated creative tasks

2. **LLM-level domain restriction**
   - the prompt instructs the model to return no SQL for out-of-domain requests
   - if the request is unrelated, the system returns a rejection response instead of generating an answer

### Example Rejection
> This system is designed to answer questions related to the provided dataset only.

This ensures that the assistant remains grounded and does not drift into unsupported topics.

---

## Example Queries Supported
The system is designed to support queries such as:
- Which products are associated with the highest number of billing documents?
- Trace the full flow of a given billing document
- Identify sales orders with incomplete flows
- Which billing documents were cancelled?
- Show customers and their related addresses
- Find products linked to the most order or billing activity

---

## API Overview
Example backend routes:
- `GET /api/graph` — fetch graph nodes and edges
- `GET /api/graph/expand/{node_id}` — expand relationships around a node
- `GET /api/stats` — fetch graph statistics
- `POST /api/chat` — submit a natural language query

---

## Tech Stack
### Backend
- Python
- FastAPI
- SQLite
- pandas
- NetworkX
- python-dotenv

### Frontend
- React
- Vite
- Cytoscape.js
- Axios

### LLM
- Groq (free-tier usage)

---

## Setup Instructions

### Backend
1. Navigate to the backend directory
2. Install dependencies
3. Add your Gemini API key in `.env`
4. Load the dataset into SQLite
5. Start the FastAPI server

Example:

```bash
cd backend
pip install -r requirements.txt
python db.py
uvicorn main:app --reload --port 8000