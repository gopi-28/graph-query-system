# AI Coding Session Logs / Summary

## Tools Used
- Claude
- ChatGPT

## Overview
I used AI tools as part of my development workflow for this assignment, mainly for:
- understanding the task requirements
- planning the project architecture
- reviewing the dataset structure
- reasoning about graph modelling
- generating and refining parts of the backend and frontend
- debugging environment and setup issues
- preparing submission materials such as the README and AI log summary

The tools were used as assistants for planning, iteration, troubleshooting, and documentation. All code and setup steps were reviewed and tested locally during development.

---

## How I Used Claude

Claude was my primary AI coding assistant during the implementation phase.

### 1. Task Understanding and Planning
I used Claude to break the assignment into phases and identify a practical stack and workflow.

This included:
- understanding the graph-based modeling goal
- deciding to use FastAPI, SQLite, NetworkX, React (Vite), Cytoscape.js, and Gemini
- planning the folder structure for backend and frontend
- sequencing the work into setup, data loading, graph construction, API development, frontend, and deployment

Example prompts:
- "Read the task file and guide me how to complete the project fully and detailly in a good way"
- "To begin this project, give step by step instruction. First what tools we are going to use and what I need to download in my laptop?"
- "Is this task easy?"
- "Can you do this full task on your own and give it to me"

### 2. Dataset Review and Graph Modelling
I used Claude to inspect the dataset and reason about what should become graph nodes and edges.

This included:
- understanding the available business entities
- identifying relationships across sales orders, deliveries, billing documents, customers, products, journal entries, and payments
- refining the graph model after seeing more of the dataset
- checking whether preprocessing or data cleaning was needed

Example prompts:
- "First read this data"
- "Do I need to clean the data or the data is good?"
- "How to show the data set to you?"

### 3. Backend and Frontend Scaffolding
Claude helped generate and explain the structure of the backend and frontend files.

This included:
- `db.py` for loading dataset files into SQLite
- `graph.py` for graph construction
- `llm.py` for natural-language-to-query flow and guardrails
- `main.py` for FastAPI APIs
- React components for graph view, chat panel, and app layout

Example prompts:
- "Write the code and explain reason for the code and usage"
- "Should I keep all this file in PyCharm? Say detaily about how to paste this code and how to make it work"
- "Give next"

### 4. Debugging and Iteration
Claude was used heavily for debugging local setup issues and environment problems.

This included:
- wrong working directory issues
- `requirements.txt` not found
- `uvicorn` not recognized
- interpreter / virtual environment mismatch
- frontend folder created in the wrong location
- issues copying and opening generated frontend files

Debugging pattern:
1. run command locally
2. observe error
3. paste exact terminal output into Claude
4. apply suggested fix
5. rerun locally
6. continue until resolved

This iterative workflow helped get the backend server running and the graph APIs working locally.

---

## How I Used ChatGPT

I used ChatGPT mainly for submission preparation, documentation, and organizing the final deliverables.

### 1. README Preparation
I used ChatGPT to help draft and structure the final `README.md` based on the task instructions.

This included:
- converting the assignment requirements into a clear project README
- writing sections for architecture, database choice, graph modelling, prompting strategy, guardrails, setup instructions, and deployment placeholders
- making the README cleaner and more reviewer-friendly

Example prompts:
- "Wait ill give the task instruction. so that you can wrute the read,md file clearly"
- "Do i need to include the read.md file in my code file or can i keep theh read.me file in the git seperate"

### 2. AI Log Preparation
I used ChatGPT to help prepare this AI coding session summary in a format suitable for submission.

This included:
- turning the actual development workflow into a structured markdown summary
- making sure the write-up honestly reflected how Claude and ChatGPT were used
- organizing the content around prompt quality, debugging workflow, and iteration patterns

Example prompts:
- "help me to prepare the ai logs for this project"
- "also include chatgpt for making the readme.md files and also the ai logs"

### 3. Submission Clarification
I used ChatGPT to clarify what the submission fields meant and how to handle them.

This included:
- understanding what to provide for AI coding session logs
- understanding what counts as a live demo / deployed application
- clarifying where `README.md` should live in the repository
- understanding that formal logs can be replaced by a summary when needed

Example prompts:
- "AI coding session logs from tools such as Cursor, Claude Code, Copilot, etc. how to do this?"
- "I used only the claud in the seperate project file. now how to show the proof"
- "Live Demo / Deployed Application Link to a deployed version of your application"

### 4. Problem Review from Existing Project Chat
I also used ChatGPT to read the previous Claude project conversation and summarize what was already done versus what was still pending.

This included:
- identifying that the backend was already working
- identifying that the main gap was the frontend and submission materials
- summarizing the practical next steps

---

## Representative Prompt Patterns

### Planning Pattern
Used AI to break the assignment into phases before implementation.
- understand requirements
- choose stack
- define architecture
- plan file structure
- move step by step

### Dataset Reasoning Pattern
Used AI to inspect the dataset and infer graph relationships.
- inspect data
- identify key entities
- map relations
- define nodes and edges

### Error-Driven Debugging Pattern
Used AI to troubleshoot based on exact runtime errors.
- run command
- paste error
- receive diagnosis
- retry with corrected command

### Documentation Pattern
Used AI to transform project work into submission-ready documentation.
- interpret requirement
- draft README
- summarize AI usage
- refine wording for clarity

---

## Debugging Workflow Summary
My debugging workflow across the project was iterative:
1. execute a setup or code step locally
2. inspect terminal or browser output
3. ask AI about the exact issue
4. apply the suggested fix manually
5. rerun and validate
6. continue to the next blocker

This workflow was used for:
- Python package setup
- path and terminal issues
- FastAPI startup
- frontend setup
- submission preparation questions

---

## What Was AI-Assisted vs Manual

### AI-assisted
- understanding the task
- architecture planning
- dataset interpretation
- graph modelling guidance
- backend and frontend scaffolding
- environment troubleshooting
- prompting strategy
- README drafting
- AI logs drafting
- submission requirement clarification

### Manual
- setting up the project in PyCharm
- downloading and placing the dataset
- installing packages
- running terminal commands
- creating files
- pasting and editing code
- testing locally
- reviewing outputs
- preparing the final submission

---

## Notes on Use
AI outputs were used as guidance and support, not accepted blindly. Suggestions were reviewed, tested locally, and adjusted based on actual runtime behavior, project constraints, and the assignment requirements.

---

## Final Summary
Claude was used primarily for coding support, architecture planning, dataset reasoning, and debugging.

ChatGPT was used primarily for documentation support, submission preparation, README drafting, AI log drafting, and summarizing the state of the project.

Together, these tools supported:
- planning
- implementation
- debugging
- iteration
- documentation
- submission preparation