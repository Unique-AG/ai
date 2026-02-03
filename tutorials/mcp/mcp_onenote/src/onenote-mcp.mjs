#!/usr/bin/env node

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createOneNoteServer, ensureGraphClient } from './server-logic.mjs';

async function main() {
  try {
    // Pre-warm the Graph client
    console.error('Initializing Graph client...');
    try {
      await ensureGraphClient();
      console.error('Graph client initialized.');
    } catch (authError) {
      console.error('Warning: Could not pre-initialize Graph client:', authError.message);
      console.error('You may need to run autentication first');
    }

    const server = createOneNoteServer();

    // Connect to standard I/O
    const transport = new StdioServerTransport();
    await server.connect(transport);
    
    console.error('Server started successfully (Stdio).');
    console.error('Use the "authenticate" tool to start the authentication flow,');
    console.error('or use "saveAccessToken" if you already have a token.');
    
    // Keep the process alive
    process.on('SIGINT', () => {
      process.exit(0);
    });
  } catch (error) {
    console.error('Error starting server:', error);
    process.exit(1);
  }
}

main();
