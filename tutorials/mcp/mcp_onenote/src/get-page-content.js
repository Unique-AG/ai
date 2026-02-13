import { Client } from '@microsoft/microsoft-graph-client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path for storing the access token
const tokenFilePath = path.join(__dirname, '.access-token.txt');

async function getPageContent() {
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

    // Get all pages
    console.log('Fetching pages...');
    const pagesResponse = await client.api('/me/onenote/pages').get();
    
    if (pagesResponse.value.length === 0) {
      console.log('No pages found.');
      return;
    }
    
    // Use the first page
    const page = pagesResponse.value[0];
    console.log(`Using page: "${page.title}" (ID: ${page.id})`);
    
    // Test different methods to get content
    
    console.log('\nMethod 1: Using /content endpoint');
    try {
      const content1 = await client.api(`/me/onenote/pages/${page.id}/content`).get();
      console.log('Success! Content type:', typeof content1);
      console.log('Content snippet:', typeof content1 === 'string' ? 
                  content1.substring(0, 100) + '...' : 
                  JSON.stringify(content1).substring(0, 100) + '...');
    } catch (error) {
      console.error('Method 1 failed:', error.message);
    }
    
    console.log('\nMethod 2: Using /content with header');
    try {
      const content2 = await client.api(`/me/onenote/pages/${page.id}/content`)
        .header('Accept', 'text/html')
        .get();
      console.log('Success! Content type:', typeof content2);
      console.log('Content snippet:', typeof content2 === 'string' ? 
                  content2.substring(0, 100) + '...' : 
                  JSON.stringify(content2).substring(0, 100) + '...');
    } catch (error) {
      console.error('Method 2 failed:', error.message);
    }
    
    console.log('\nMethod 3: Using contentUrl directly');
    try {
      console.log('ContentUrl:', page.contentUrl);
      const content3 = await client.api(page.contentUrl).get();
      console.log('Success! Content type:', typeof content3);
      console.log('Content snippet:', typeof content3 === 'string' ? 
                  content3.substring(0, 100) + '...' : 
                  JSON.stringify(content3).substring(0, 100) + '...');
    } catch (error) {
      console.error('Method 3 failed:', error.message);
    }
    
    console.log('\nMethod 4: Using contentUrl with header');
    try {
      const content4 = await client.api(page.contentUrl)
        .header('Accept', 'text/html')
        .get();
      console.log('Success! Content type:', typeof content4);
      console.log('Content snippet:', typeof content4 === 'string' ? 
                  content4.substring(0, 100) + '...' : 
                  JSON.stringify(content4).substring(0, 100) + '...');
    } catch (error) {
      console.error('Method 4 failed:', error.message);
    }
    
    console.log('\nMethod 5: Using contentUrl with responseType "raw"');
    try {
      const content5 = await client.api(page.contentUrl)
        .responseType('raw')
        .get();
      console.log('Success! Raw response type:', typeof content5);
      if (content5 && content5.body) {
        const text = await content5.text();
        console.log('Content snippet from raw response:', text.substring(0, 100) + '...');
      } else {
        console.log('Raw response does not have a body property');
      }
    } catch (error) {
      console.error('Method 5 failed:', error.message);
    }

  } catch (error) {
    console.error('Error:', error);
  }
}

getPageContent();
