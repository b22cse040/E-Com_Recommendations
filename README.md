# E-Com_Recommendations
A RAG based product recommendation for interior decoration for Sparkathon 2025.

## Introduction
This project is a RAG-based interior design product recommendation chatbot that helps users find furniture and decor items through natural language queries. When a user enters a query, the system first retrieves relevant product chunks from Elasticsearch and then uses a language model to generate clear, friendly product descriptions and explanations. In parallel, it also searches for semantically similar queries ("users also searched for") and pre-generates their responses, so they’re ready instantly when the user clicks on them. The frontend, built with Streamlit, displays the main recommendations first and provides interactive buttons for similar queries without re-calling the LLM, ensuring a fast and smooth user experience. Overall, the project currently integrates query understanding, retrieval, generation, and interactive frontend logic in a seamless flow.

## User Story
![image](https://github.com/user-attachments/assets/8a6f1b9f-d7bd-4051-b107-965cf924944e)
