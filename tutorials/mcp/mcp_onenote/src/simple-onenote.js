import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path for storing the access token
const tokenFilePath = path.join(__dirname, '.access-token.txt');

async function listNotebooks() {
  try {
    // Read the access token
    if (!fs.existsSync(tokenFilePath)) {
      console.error('Access token not found. Please authenticate first.');
      return;
    }

    const tokenData = fs.readFileSync(tokenFilePath, 'utf8');
    let accessToken;
    
    try {
      // Try to parse as JSON first (new format)
      const parsedToken = JSON.parse(tokenData);
      accessToken = parsedToken.token;
    } catch (parseError) {
      // Fall back to using the raw token (old format)
      accessToken = tokenData;
    }

    if (!accessToken) {
      console.error('Access token not found in file.');
      return;
    }

    // Create Microsoft Graph client
    const client = Client.init({
      authProvider: (done) => {
        done(null, accessToken);
      }
    });

    // Get notebooks
    console.log('Fetching notebooks...');
    const response = await client.api('/me/onenote/notebooks').get();
    
    console.log('\nYour OneNote Notebooks:');
    console.log('=======================');
    
    if (response.value.length === 0) {
      console.log('No notebooks found.');
    } else {
      response.value.forEach((notebook, index) => {
        console.log(`${index + 1}. ${notebook.displayName}`);
      });
    }

  } catch (error) {
    console.error('Error listing notebooks:', error);
  }
}

// Run the function
listNotebooks(); 