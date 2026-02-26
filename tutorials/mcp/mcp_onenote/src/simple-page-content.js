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
async function getPageContent() {
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
    console.log("Fetching pages...");
    const pages = await client.api('/me/onenote/pages').get();
    
    if (!pages || !pages.value || pages.value.length === 0) {
      console.log("No pages found");
      return;
    }
    
    // Choose the first page
    const page = pages.value[0];
    console.log(`Using page: "${page.title}" (ID: ${page.id})`);
    
    // Try to get the content
    console.log("Fetching page content...");
    
    try {
      // Create direct HTTP request to the content endpoint
      const url = `https://graph.microsoft.com/v1.0/me/onenote/pages/${page.id}/content`;
      console.log(`Making request to: ${url}`);
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}`);
      }
      
      const contentType = response.headers.get('content-type');
      console.log(`Content type: ${contentType}`);
      
      const content = await response.text();
      console.log(`Content received! Length: ${content.length} characters`);
      console.log(`Content preview (first 100 chars): ${content.substring(0, 100).replace(/\n/g, ' ')}...`);
      
      // Don't save content to file - just confirm it worked
      console.log("Content retrieval successful! Privacy preserved - not saving to disk.");
    } catch (error) {
      console.error("Error fetching content:", error);
    }
    
  } catch (error) {
    console.error("Error:", error);
  }
}

// Run the function
getPageContent(); 