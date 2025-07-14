# E-Com_Recommendations
A RAG based product recommendation for interior decoration.

## Introduction
This project is a RAG-based interior design product recommendation chatbot that helps users find furniture and decor items through natural language queries. When a user enters a query, the system first retrieves relevant product chunks from Elasticsearch and then uses a language model to generate clear, friendly product descriptions and explanations. In parallel, it also searches for semantically similar queries ("users also searched for") and pre-generates their responses, so they’re ready instantly when the user clicks on them. The frontend, built with Streamlit, displays the main recommendations first and provides interactive buttons for similar queries without re-calling the LLM, ensuring a fast and smooth user experience. Overall, the project currently integrates query understanding, retrieval, generation, and interactive frontend logic in a seamless flow.

All the queries that have been searched will be cached for the next 2 hours. This will minimize the response timing and the amount of LLM calls made.
Whenever a new query is entered, it is compared to all the cached queries to check for any similar queries, if there exists any such query, the result will be presented in under 0.1 sec.

Finally, for the user, we have made a minimalist UI to prevent any confusion for the user.

## User Story
![image](https://github.com/user-attachments/assets/8a6f1b9f-d7bd-4051-b107-965cf924944e)

## UI
Screenshots of the UI have been kept in the screenshots directory