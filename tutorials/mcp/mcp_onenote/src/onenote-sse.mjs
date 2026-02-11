import express from 'express';
import cors from 'cors';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { createOneNoteServer, ensureGraphClient } from './server-logic.mjs';

const app = express();
const port = process.env.PORT || 3000;

// TODO: Add Zitadel auth layer to protect SSE/message endpoints
app.use(cors());

// Parse JSON bodies for POST requests
app.use(express.json());

// Pre-warm the Graph client
console.log('Initializing Graph client...');
ensureGraphClient()
  .then(() => console.log('Graph client initialized.'))
  .catch(err => {
    console.error('Warning: Could not pre-initialize Graph client:', err.message);
    console.error('Use the authenticate tool to login.');
  });

const transports = new Map();

// SSE endpoint
app.get('/sse', async (req, res) => {
  console.log('New SSE connection');
  
  // Create a new transport for this connection
  // The endpoint passed here is where the client should send messages
  const transport = new SSEServerTransport('/message', res);
  
  // Create a new server instance for this connection
  const server = createOneNoteServer();
  
  // Connect the server to the transport
  await server.connect(transport);
  
  // Store the transport by sessionId so we can route messages
  transports.set(transport.sessionId, transport);
  
  // Clean up on close
  res.on('close', () => {
    console.log('SSE connection closed', transport.sessionId);
    transports.delete(transport.sessionId);
    server.close();
  });
});

// Message endpoint
app.post('/message', async (req, res) => {
  const sessionId = req.query.sessionId;
  if (!sessionId) {
    res.status(400).send('Missing sessionId query parameter');
    return;
  }
  
  const transport = transports.get(sessionId);
  if (!transport) {
    res.status(404).send('Session not found');
    return;
  }
  
  // Handle the message
  await transport.handlePostMessage(req, res, req.body);
});

app.listen(port, () => {
  console.log(`OneNote MCP Server running`);
});


