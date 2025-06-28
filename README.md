# AI-Powered SQL Query Generator

🚀 **[Live Demo](https://nlp-frontend-hau5.onrender.com)** | Try it now!

## Overview
The AI-Powered SQL Query Generator is an enterprise-grade solution designed to bridge the gap between natural language questions and complex database queries. Leveraging the advanced reasoning capabilities of Google's Gemini AI, this application interprets user intent and constructs syntactically correct SQL queries across multiple database dialects. It serves as a powerful tool for data analysts, developers, and business intelligence professionals, enabling them to extract insights without deep knowledge of SQL syntax. The system is built with a focus on accuracy, security, and scalability, making it suitable for modern data environments.

## Features
### 🚀 Multi-Dialect Support
The engine is capable of generating compliant SQL for a wide range of relational databases, including **PostgreSQL**, **MySQL**, **Snowflake**, **BigQuery**, **Redshift**, and **SQLite**. It automatically adjusts syntax, functions, and data types to match the specific target dialect.

### 🧠 schema-Aware Intelligence
Unlike generic text-to-code tools, this system accepts custom database schemas (DDL or descriptions) as context. This ensures that generated queries correctly reference your specific table names, column identifiers, and relationships, significantly reducing hallucinations and syntax errors.

### 🛡️ Robust Architecture
Built for reliability, the application includes automatic retry mechanisms for API calls, sophisticated rate-limiting handling, and comprehensive error logging. It gracefully handles transient failures and provides clear, actionable feedback to users.

## Tech Stack
- **Backend**: Python 3.11, FastAPI (High-performance async framework), Pydantic (Data validation)
- **AI Integration**: Google Gemini SDK (Generative AI models)
- **Frontend**: Streamlit (Rapid interactive UI development)
- **Resilience**: Tenacity (Retry logic and failure handling)
- **Containerization**: Docker & Docker Compose (Production-ready orchestration)

## Setup & Installation

### Prerequisites
- Docker and Docker Compose installed on your machine.
- A valid Google Gemini API Key.

### Quick Start (Docker)
1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd nlp_to_sql
    ```
2.  **Configuration**:
    Create a `.env` file in the root directory and add your API key:
    ```env
    GEMINI_API_KEY=your_actual_api_key_here
    ```
3.  **Launch Services**:
    Run the application using Docker Compose:
    ```bash
    docker-compose up --build -d
    ```
4.  **Access the App**:
    - Frontend Interface: [http://localhost:8501](http://localhost:8501)
    - Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Usage Guide
1.  **Select Database**: On the left sidebar, choose the SQL dialect you are working with (e.g., PostgreSQL).
2.  **Provide Context**: Paste your table definitions or a description of your schema in the "Schema" text area. This step is optional but highly recommended for complex queries.
3.  **Ask a Question**: Type your data question in natural language (e.g., *"Find the top 5 customers by total revenue in Q3 2024"*).
4.  **Generate**: Click the "Generate SQL" button. The AI will analyze your question and schema to produce the query.
5.  **Export**: Copy the generated SQL or download it as a `.sql` file for direct execution in your database client.

## Architecture
The system follows a microservices pattern orchestrated by Docker Compose:

- **Frontend Service (`web`)**: A stateless Streamlit application that handles user input and visualization. It communicates with the backend via RESTful API calls.
- **Backend Service (`api`)**: A FastAPI application that serves as the core logic layer. It manages:
    - **Prompt Engineering**: constructing optimized prompts for the AI model.
    - **Validation**: ensuring inputs meet required formats.
    - **AI Interaction**: securely sending requests to Google's Gemini API.
    - **Response Parsing**: cleaning and formatting the AI output into executable SQL.

This decoupled design allows for independent scaling, easier maintenance, and the potential to swap out frontend or AI components with minimal disruption to the core logic.
