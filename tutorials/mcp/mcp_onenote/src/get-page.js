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

// Get the page title from command line
const pageTitle = process.argv[2];
if (!pageTitle) {
  console.error('Please provide a page title as argument. Example: node get-page.js "Questions"');
  process.exit(1);
}

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
    
    // Get all pages
    console.log(`Searching for page with title: "${pageTitle}"...`);
    const pagesResponse = await client.api('/me/onenote/pages').get();
    
    if (!pagesResponse.value || pagesResponse.value.length === 0) {
      console.error('No pages found');
      return;
    }
    
    // Find the requested page
    const page = pagesResponse.value.find(p => 
      p.title && p.title.toLowerCase().includes(pageTitle.toLowerCase())
    );
    
    if (!page) {
      console.error(`No page found with title containing "${pageTitle}"`);
      console.log('Available pages:');
      pagesResponse.value.forEach(p => console.log(`- ${p.title}`));
      return;
    }
    
    console.log(`Found page: "${page.title}" (ID: ${page.id})`);
    
    // Fetch the content
    const url = `https://graph.microsoft.com/v1.0/me/onenote/pages/${page.id}/content`;
    console.log(`Fetching content from: ${url}`);
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}`);
    }
    
    const content = await response.text();
    console.log(`Content received! Length: ${content.length} characters`);
    
    // Extract text content
    let plainText = content
      .replace(/<[^>]*>?/gm, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    
    console.log('\n--- PAGE CONTENT ---\n');
    console.log(plainText);
    console.log('\n--- END OF CONTENT ---\n');
    
  } catch (error) {
    console.error('Error:', error);
  }
}

// Run the function
getPageContent(); 