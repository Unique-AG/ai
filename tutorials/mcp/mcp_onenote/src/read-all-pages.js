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

// Extract readable text from HTML
function extractReadableText(html) {
  try {
    const dom = new JSDOM(html);
    const document = dom.window.document;
    
    // Remove scripts
    const scripts = document.querySelectorAll('script');
    scripts.forEach(script => script.remove());
    
    // Extract text from each paragraph, list item, heading, etc. and preserve structure
    let text = '';
    
    // Process headings
    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
      text += `\n${heading.textContent.trim()}\n${'-'.repeat(heading.textContent.length)}\n`;
    });
    
    // Process paragraphs
    document.querySelectorAll('p').forEach(paragraph => {
      const content = paragraph.textContent.trim();
      if (content) {
        text += `${content}\n\n`;
      }
    });
    
    // Process lists
    document.querySelectorAll('ul, ol').forEach(list => {
      text += '\n';
      list.querySelectorAll('li').forEach((item, index) => {
        const content = item.textContent.trim();
        if (content) {
          text += `${index + 1}. ${content}\n`;
        }
      });
      text += '\n';
    });
    
    // Process divs and spans (might contain important content)
    document.querySelectorAll('div, span').forEach(element => {
      // Only include direct text nodes that are not already included via paragraphs, lists, etc.
      if (element.childNodes.length === 1 && element.childNodes[0].nodeType === 3) {
        const content = element.textContent.trim();
        if (content) {
          text += `${content}\n\n`;
        }
      }
    });
    
    // Process tables
    document.querySelectorAll('table').forEach(table => {
      text += '\nTable content:\n';
      table.querySelectorAll('tr').forEach(row => {
        const cells = Array.from(row.querySelectorAll('td, th'))
          .map(cell => cell.textContent.trim())
          .join(' | ');
        text += `${cells}\n`;
      });
      text += '\n';
    });
    
    // Fallback: If no specific elements were processed, get all body text
    if (!text.trim()) {
      text = document.body.textContent.trim().replace(/\s+/g, ' ');
    }
    
    return text;
  } catch (error) {
    console.error('Error extracting text:', error);
    return 'Error: Could not extract readable text from HTML content.';
  }
}

// Main function
async function readAllPages() {
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
    
    console.log(`Found ${pages.value.length} pages. Reading full content for each...\n`);
    
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
        
        const htmlContent = await response.text();
        const readableText = extractReadableText(htmlContent);
        
        console.log(readableText);
        console.log("\n");
      } catch (error) {
        console.error(`Error processing ${page.title}:`, error.message);
      }
    }
    
    console.log("\nAll pages have been read. You can now ask questions about their content.");
    
  } catch (error) {
    console.error("Error:", error);
  }
}

// Run the function
readAllPages(); 