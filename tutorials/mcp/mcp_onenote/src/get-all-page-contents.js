#!/usr/bin/env node

import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { JSDOM } from 'jsdom';

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

// Function to extract text content from HTML
function extractTextContent(html) {
  try {
    const dom = new JSDOM(html);
    const document = dom.window.document;
    
    // Extract main content
    const bodyText = document.body.textContent.trim();
    
    // Create a summary (first 300 chars or so)
    const summary = bodyText.substring(0, 300).replace(/\s+/g, ' ');
    
    return summary.length < bodyText.length 
      ? `${summary}...` 
      : summary;
  } catch (error) {
    console.error('Error extracting text:', error);
    return 'Could not extract text content';
  }
}

// Main function
async function getAllPageContents() {
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
    
    console.log(`Found ${pages.value.length} pages. Fetching content for each...`);
    
    // Process each page
    for (const page of pages.value) {
      console.log(`\n===== ${page.title} =====`);
      
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
        const textSummary = extractTextContent(content);
        
        console.log(`Last modified: ${new Date(page.lastModifiedDateTime).toLocaleString()}`);
        console.log(`Content summary: ${textSummary}`);
      } catch (error) {
        console.error(`Error processing ${page.title}:`, error.message);
      }
    }
    
  } catch (error) {
    console.error("Error:", error);
  }
}

// Run the function
getAllPageContents(); 