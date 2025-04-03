# Metadata Extractor

## Description

This is a application that showcases how to interact with the Unique API using the SDK and the GraphQL APIs of the Unique Platform directly. It listens for ingestion finished events from the Unique API and then extracts metadata from the ingested documents. The app either connects to the local app using webhook or connects to a event socket. 

In addition, a script (see src/scripts/batch_metadata.py) shows how to extract metadata from a filename in a batch job.

## Setup

1. Create a Service User in Zitadel (see .env.example file)
2. Grant Service User access to relevant Scopes in the Knowledge Base

## Running the server

1. Add .env file using .env.example as template
2. Run `poetry install` in the root directory
3. Run `poetry run start` in the root directory to start the server