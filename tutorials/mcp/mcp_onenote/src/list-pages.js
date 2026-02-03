import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path for storing the access token
const tokenFilePath = path.join(__dirname, '.access-token.txt');

async function listPages() {
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

    // First, get all notebooks
    console.log('Fetching notebooks...');
    const notebooksResponse = await client.api('/me/onenote/notebooks').get();
    
    if (notebooksResponse.value.length === 0) {
      console.log('No notebooks found.');
      return;
    }

    // Use the first notebook (you can modify this to select a specific notebook)
    const notebook = notebooksResponse.value[0];
    console.log(`Using notebook: "${notebook.displayName}"`);

    // Get sections in the selected notebook
    console.log(`Fetching sections in "${notebook.displayName}" notebook...`);
    const sectionsResponse = await client.api(`/me/onenote/notebooks/${notebook.id}/sections`).get();
    
    if (sectionsResponse.value.length === 0) {
      console.log('No sections found in this notebook.');
      return;
    }

    // Use the first section (you can modify this to select a specific section)
    const section = sectionsResponse.value[0];
    console.log(`Using section: "${section.displayName}"`);

    // Get pages in the section
    console.log(`Fetching pages in "${section.displayName}" section...`);
    const pagesResponse = await client.api(`/me/onenote/sections/${section.id}/pages`).get();
    
    console.log(`\nPages in ${section.displayName}:`);
    console.log('=====================');
    
    if (pagesResponse.value.length === 0) {
      console.log('No pages found.');
    } else {
      pagesResponse.value.forEach((page, index) => {
        console.log(`${index + 1}. ${page.title} (Created: ${new Date(page.createdDateTime).toLocaleString()})`);
      });
    }

  } catch (error) {
    console.error('Error listing pages:', error);
  }
}

// Run the function
listPages(); 