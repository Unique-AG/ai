import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path for storing the access token
const tokenFilePath = path.join(__dirname, '.access-token.txt');

async function createPage() {
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

    // Create a new page
    console.log(`Creating a new page in "${section.displayName}" section...`);
    
    // Current date and time
    const now = new Date();
    const formattedDate = now.toISOString().split('T')[0];
    const formattedTime = now.toLocaleTimeString();
    
    // Create simple HTML content
    const simpleHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Created via MCP on ${formattedDate}</title>
        </head>
        <body>
          <h1>Created via MCP on ${formattedDate}</h1>
          <p>This page was created via the Microsoft Graph API at ${formattedTime}.</p>
          <p>This demonstrates that the OneNote MCP integration is working correctly!</p>
          <ul>
            <li>The authentication flow is working</li>
            <li>We can create new pages</li>
            <li>We can access existing notebooks</li>
          </ul>
        </body>
      </html>
    `;
    
    const response = await client
      .api(`/me/onenote/sections/${section.id}/pages`)
      .header("Content-Type", "application/xhtml+xml")
      .post(simpleHtml);
    
    console.log(`\nNew page created successfully:`);
    console.log(`Title: ${response.title}`);
    console.log(`Created: ${new Date(response.createdDateTime).toLocaleString()}`);
    console.log(`Link: ${response.links.oneNoteWebUrl.href}`);

  } catch (error) {
    console.error('Error creating page:', error);
  }
}

// Run the function
createPage(); 