#!/usr/bin/env node

import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path for storing the access token
const tokenFilePath = path.join(__dirname, '.access-token.txt');

// Function to read the access token
function getAccessToken() {
  try {
    const tokenData = fs.readFileSync(tokenFilePath, 'utf8');
    try {
      // Try to parse as JSON first (new format)
      const parsedToken = JSON.parse(tokenData);
      return parsedToken.token;
    } catch (parseError) {
      // Fall back to using the raw token (old format)
      return tokenData;
    }
  } catch (error) {
    console.error('Error reading token:', error);
    return null;
  }
}

// Main function
async function getAllPagesFullContent() {
  try {
    // Get the access token
    const accessToken = getAccessToken();
    if (!accessToken) {
      console.error('No access token found');
      return;
    }
    
    // Initialize Graph client
    const client = Client.init({
      authProvider: (done) => {
        done(null, accessToken);
      }
    });
    
    // List pages
    console.log("Fetching all pages...");
    const pages = await client.api('/me/onenote/pages').get();
    
    if (!pages || !pages.value || pages.value.length === 0) {
      console.log("No pages found");
      return;
    }
    
    console.log(`Found ${pages.value.length} pages. Fetching full content for each...\n`);
    
    // Process each page
    for (const page of pages.value) {
      console.log(`\n==================================================================`);
      console.log(`PAGE: ${page.title}`);
      console.log(`Last modified: ${new Date(page.lastModifiedDateTime).toLocaleString()}`);
      console.log(`==================================================================\n`);
      
      try {
        // Create direct HTTP request to the content endpoint
        const url = page.contentUrl;
        
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        });
        
        if (!response.ok) {
          console.error(`Error fetching ${page.title}: ${response.status} ${response.statusText}`);
          continue;
        }
        
        const content = await response.text();
        
        // Extract text content from HTML for easier reading
        console.log("FULL HTML CONTENT:");
        console.log(content);
        console.log("\n");
      } catch (error) {
        console.error(`Error processing ${page.title}:`, error.message);
      }
    }
    
  } catch (error) {
    console.error("Error:", error);
  }
}

// Run the function
getAllPagesFullContent(); 