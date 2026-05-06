import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { Client } from '@microsoft/microsoft-graph-client';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import { PublicClientApplication } from '@azure/msal-node';
import fetch from 'node-fetch';
import dotenv from 'dotenv';
import { z } from 'zod';

// Load environment variables
dotenv.config();

// Get the current file's directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Client ID for Microsoft Graph API access
const clientId = '14d82eec-204b-4c2f-b7e8-296a70dab67e'; // Microsoft Graph Explorer client ID
const scopes = ['Notes.Read.All', 'Notes.ReadWrite.All', 'User.Read', 'offline_access'];
const cacheFilePath = path.join(__dirname, '.msal-cache.json');

// Shared state
let accessToken = null;
let graphClient = null;
let pca = null;

// Initialize MSAL client with cache from env var or file
function getMsalClient() {
  if (!pca) {
    const msalConfig = {
      auth: {
        clientId: clientId,
        authority: 'https://login.microsoftonline.com/common'
      }
    };
    pca = new PublicClientApplication(msalConfig);
    
    // Priority: env var > file
    if (process.env.MSAL_CACHE) {
      const cacheData = Buffer.from(process.env.MSAL_CACHE, 'base64').toString('utf8');
      pca.getTokenCache().deserialize(cacheData);
      console.error('Loaded MSAL cache from MSAL_CACHE env var');
    } else if (fs.existsSync(cacheFilePath)) {
      const cacheData = fs.readFileSync(cacheFilePath, 'utf8');
      pca.getTokenCache().deserialize(cacheData);
      console.error('Loaded MSAL cache from file');
    } else {
      console.error('No MSAL cache found - use authenticate tool to login');
    }
  }
  return pca;
}

// Save cache to file (for local dev) and return base64 for env var
function saveCache() {
  if (pca) {
    const cacheData = pca.getTokenCache().serialize();
    fs.writeFileSync(cacheFilePath, cacheData);
    return Buffer.from(cacheData).toString('base64');
  }
  return null;
}

// Get access token (auto-refreshes using MSAL's acquireTokenSilent)
async function getAccessToken() {
  const client = getMsalClient();
  const accounts = await client.getTokenCache().getAllAccounts();
  
  if (accounts.length === 0) {
    throw new Error("No cached account. Use 'authenticate' tool first.");
  }
  
  try {
    const silentRequest = {
      account: accounts[0],
      scopes: scopes
    };
    const response = await client.acquireTokenSilent(silentRequest);
    saveCache();
    return response.accessToken;
  } catch (error) {
    console.error('Silent token acquisition failed:', error.message);
    throw new Error("Token refresh failed. Use 'authenticate' tool to re-login.");
  }
}

// Function to ensure Graph client is created
export async function ensureGraphClient() {
  accessToken = await getAccessToken();
  graphClient = Client.init({
    authProvider: (done) => {
      done(null, accessToken);
    }
  });
  return graphClient;
}

export function createOneNoteServer() {
  const server = new McpServer(
    { 
      name: "onenote",
      version: "1.0.0",
      description: "OneNote MCP Server" 
    },
    {
      capabilities: {
        tools: {
          listChanged: true
        }
      }
    }
  );

  // Tool for starting authentication flow with device code
  server.tool(
    "authenticate",
    "Start device code authentication flow to login with a Microsoft account. Returns URL and code - complete login in browser, then call again to confirm.",
    {
      force: z.boolean().optional().describe("Force re-authentication even if already logged in")
    },
    async (params) => {
      console.error("Authenticate tool called with force:", params.force);
      
      // Check if we already have a valid token (unless force=true)
      if (!params.force) {
        try {
          const client = getMsalClient();
          const accounts = await client.getTokenCache().getAllAccounts();
          if (accounts.length > 0) {
            return {
              content: [{
                type: "text",
                text: `Already authenticated as ${accounts[0].username}. Use force: true to re-authenticate with a different account.`
              }]
            };
          }
        } catch (e) {
          // Continue to auth flow
        }
      }
      
      // Clear cache for fresh login
      if (fs.existsSync(cacheFilePath)) {
        fs.unlinkSync(cacheFilePath);
        console.error("Cleared existing token cache");
      }
      pca = null; // Reset MSAL client
      
      const client = getMsalClient();
      let deviceCodeMessage = "";
      
      // Start auth with timeout - return URL quickly, continue in background
      const authPromise = client.acquireTokenByDeviceCode({
        scopes: scopes,
        deviceCodeCallback: (response) => {
          deviceCodeMessage = response.message;
          console.error("Device code:", response.message);
        }
      });
      
      // Wait for either: auth to complete OR 3 seconds (to show URL)
      const timeoutPromise = new Promise((resolve) => 
        setTimeout(() => resolve({ timeout: true }), 3000)
      );
      
      const result = await Promise.race([authPromise, timeoutPromise]);
      
      if (result.timeout) {
        authPromise.then((tokenResponse) => {
          saveCache();
          graphClient = null;
          accessToken = null;
          console.error(`Auth completed for ${tokenResponse.account.username.split('@')[0].slice(0, 3)}***`);
        }).catch(err => console.error("Background auth failed:", err.message));
        
        return {
          content: [{
            type: "text",
            text: `🔐 Authentication started!\n\n${deviceCodeMessage}\n\n⏳ Complete login in browser. Token is kept in memory (~1h), MSAL refreshes automatically.`
          }]
        };
      } else {
        saveCache();
        graphClient = null;
        accessToken = null;
        
        return {
          content: [{
            type: "text",
            text: `✅ Authenticated as ${result.account.username}\nToken expires: ${result.expiresOn.toLocaleString()}`
          }]
        };
      }
    }
  );

  // Disabled: exposes token cache to MCP clients. Re-enable if persistent auth via MSAL_CACHE env var is needed.
  // server.tool(
  //   "get_auth_cache",
  //   "Get the current auth cache as base64 string to set as MSAL_CACHE env var in Azure",
  //   {},
  //   async () => {
  //     const client = getMsalClient();
  //     const accounts = await client.getTokenCache().getAllAccounts();
  //     
  //     if (accounts.length === 0) {
  //       return {
  //         content: [{
  //           type: "text",
  //           text: "❌ No authenticated account. Use 'authenticate' tool first."
  //         }]
  //       };
  //     }
  //     
  //     const cacheData = client.getTokenCache().serialize();
  //     const base64Cache = Buffer.from(cacheData).toString('base64');
  //     
  //     return {
  //       content: [{
  //         type: "text",
  //         text: `✅ Authenticated as: ${accounts[0].username}\n\n📋 Set this env var in Azure to persist:\n\nMSAL_CACHE=${base64Cache}`
  //       }]
  //     };
  //   }
  // );

  // Tool for listing all notebooks
  server.tool(
    "listNotebooks",
    "List all OneNote notebooks",
    {
      includeSections: z.boolean().optional().describe("Include sections in the response (optional)")
    },
    async (params) => {
      console.error("listNotebooks tool called");
      try {
        await ensureGraphClient();
        let api = graphClient.api("/me/onenote/notebooks");
        if (params.includeSections) {
          api = api.expand("sections");
        }
        const response = await api.get();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(response.value)
            }
          ]
        };
      } catch (error) {
        console.error("Error listing notebooks:", error);
        throw new Error(`Failed to list notebooks: ${error.message}`);
      }
    }
  );

  // Tool for getting notebook details
  server.tool(
    "getNotebook",
    "Get details of a specific notebook",
    {
      notebookId: z.string().optional().describe("ID of the notebook (optional)"),
    },
    async (params) => {
      try {
        await ensureGraphClient();
        if (params.notebookId) {
          const notebook = await graphClient.api(`/me/onenote/notebooks/${params.notebookId}`).get();
          return { content: [{ type: "text", text: JSON.stringify(notebook) }] };
        }
        const response = await graphClient.api(`/me/onenote/notebooks`).get();
        if (!response.value || response.value.length === 0) {
          throw new Error("No notebooks found");
        }
        return { content: [{ type: "text", text: JSON.stringify(response.value[0]) }] };
      } catch (error) {
        console.error("Error getting notebook:", error);
        throw new Error(`Failed to get notebook: ${error.message}`);
      }
    }
  );

  // Tool for listing sections in a notebook
  server.tool(
    "listSections",
    "List all sections in a notebook",
    {
      notebookId: z.string().optional().describe("Filter by notebook ID (optional)")
    },
    async (params) => {
      console.error("listSections tool called");
      try {
        await ensureGraphClient();
        const endpoint = params.notebookId
          ? `/me/onenote/notebooks/${params.notebookId}/sections`
          : `/me/onenote/sections`;
        const response = await graphClient.api(endpoint).get();
        return { content: [{ type: "text", text: JSON.stringify(response.value) }] };
      } catch (error) {
        console.error("Error listing sections:", error);
        throw new Error(`Failed to list sections: ${error.message}`);
      }
    }
  );

  // Tool for listing pages in a section
  server.tool(
    "listPages",
    "List all pages in a section",
    {
      sectionId: z.string().optional().describe("Filter by section ID (optional)")
    },
    async (params) => {
      console.error("listPages tool called");
      try {
        await ensureGraphClient();

        let sectionId = params.sectionId;
        if (!sectionId) {
          const sectionsResponse = await graphClient.api(`/me/onenote/sections`).get();
          if (sectionsResponse.value.length === 0) {
            return { content: [{ type: "text", text: "[]" }] };
          }
          sectionId = sectionsResponse.value[0].id;
        }

        const response = await graphClient.api(`/me/onenote/sections/${sectionId}/pages`).get();
        
        return { 
          content: [
            {
              type: "text",
              text: JSON.stringify(response.value)
            }
          ]
        };
      } catch (error) {
        console.error("Error listing pages:", error);
        throw new Error(`Failed to list pages: ${error.message}`);
      }
    }
  );

  // Tool for getting the content of a page
  server.tool(
    "getPage",
    "Get the content of a page",
    {
      page_id: z.string().optional().describe("ID of the page to retrieve (optional)"),
      search_term: z.string().optional().describe("Search term to find a page by title if ID is not found (optional)"),
    },
    async (params) => {
      try {
        console.error("GetPage called with params:", params);
        await ensureGraphClient();
        
        // First, list all pages to find the one we want
        const pagesResponse = await graphClient.api('/me/onenote/pages').get();
        console.error("Got", pagesResponse.value.length, "pages");
        
        let targetPage;
        const pageId = params.page_id;
        const searchTerm = params.search_term;
        
        // If a page ID is provided, use it to find the page
        if (pageId && pageId.length > 0) {
          console.error("Looking for page with ID:", pageId);
          
          // Look for exact match first
          targetPage = pagesResponse.value.find(p => p.id === pageId);
          
          // If no exact match, try partial ID match
          if (!targetPage) {
             console.error("No exact match, trying partial ID match");
             targetPage = pagesResponse.value.find(p => 
               p.id.includes(pageId) || pageId.includes(p.id)
             );
          }
        } 
        
        // If still no match and search term provided, try matching by title
        if (!targetPage && searchTerm && searchTerm.length > 0) {
           console.error("No exact ID match, trying title search with:", searchTerm);
           targetPage = pagesResponse.value.find(p => 
             p.title && p.title.toLowerCase().includes(searchTerm.toLowerCase())
           );
        }
        
        // If no parameters provided or no match found, use the first page
        if (!targetPage && !pageId && !searchTerm) {
          console.error("No ID or search term provided, using first page");
          targetPage = pagesResponse.value[0];
        }
        
        if (!targetPage) {
          throw new Error("Page not found");
        }
        
        console.error("Target page found:", targetPage.title);
        console.error("Page ID:", targetPage.id);
        
        try {
          const url = `https://graph.microsoft.com/v1.0/me/onenote/pages/${targetPage.id}/content`;
          console.error("Fetching content from:", url);
          
          const token = await getAccessToken();
          const response = await fetch(url, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}`);
          }
          
          const content = await response.text();
          console.error(`Content received! Length: ${content.length} characters`);
          
          // Return the raw HTML content
          return {
            content: [
              {
                type: "text",
                text: content
              }
            ]
          };
        } catch (error) {
          console.error("Error getting content:", error);
          
          // Return a simple error message
          return {
            content: [
              {
                type: "text",
                text: `Error retrieving page content: ${error.message}`
              }
            ]
          };
        }
      } catch (error) {
        console.error("Error in getPage:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error in getPage: ${error.message}`
            }
          ]
        };
      }
    }
  );

  // Tool for creating a new page in a section
  server.tool(
    "createPage",
    "Create a new page in a section",
    {
      sectionId: z.string().optional().describe("Section ID to create the page in (optional, defaults to first section)"),
      title: z.string().optional().describe("Title of the new page (optional)")
    },
    async (params) => {
      console.error("createPage tool called");
      try {
        await ensureGraphClient();

        let sectionId = params.sectionId;
        if (!sectionId) {
          const sectionsResponse = await graphClient.api(`/me/onenote/sections`).get();
          if (sectionsResponse.value.length === 0) {
            throw new Error("No sections found");
          }
          sectionId = sectionsResponse.value[0].id;
        }

        const pageTitle = (params.title || "New Page").replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const simpleHtml = `
          <!DOCTYPE html>
          <html>
            <head>
              <title>${pageTitle}</title>
            </head>
            <body>
              <p>This is a new page created via the Microsoft Graph API</p>
            </body>
          </html>
        `;
        
        const response = await graphClient
          .api(`/me/onenote/sections/${sectionId}/pages`)
          .header("Content-Type", "application/xhtml+xml")
          .post(simpleHtml);
        
        return { 
          content: [
            {
              type: "text",
              text: JSON.stringify(response)
            }
          ]
        };
      } catch (error) {
        console.error("Error creating page:", error);
        throw new Error(`Failed to create page: ${error.message}`);
      }
    }
  );

  // Tool for searching pages
  server.tool(
    "searchPages",
    "Search for pages across notebooks",
    {
      query: z.string().describe("The search term to filter pages by title"),
    },
    async (params) => {
      try {
        await ensureGraphClient();
        
        // Get all pages
        const response = await graphClient.api(`/me/onenote/pages`).get();
        
        // If search string is provided, filter the results
        if (params.query && params.query.length > 0) {
          const searchTerm = params.query.toLowerCase();
          const filteredPages = response.value.filter(page => {
            // Search in title
            if (page.title && page.title.toLowerCase().includes(searchTerm)) {
              return true;
            }
            return false;
          });
          
          return { 
            content: [
              {
                type: "text",
                text: JSON.stringify(filteredPages)
              }
            ]
          };
        } else {
          // Return all pages if no search term
          return { 
            content: [
              {
                type: "text",
                text: JSON.stringify(response.value)
              }
            ]
          };
        }
      } catch (error) {
        console.error("Error searching pages:", error);
        throw new Error(`Failed to search pages: ${error.message}`);
      }
    }
  );

  // Tool for appending content to an existing page
  server.tool(
    "appendToPage",
    "Append new content to an existing OneNote page",
    {
      page_id: z.string().describe("ID of the page to append content to"),
      content: z.string().describe("HTML content to append to the page"),
      target: z.string().optional().describe("Target element to append to (body or specific data-id). Defaults to body")
    },
    async (params) => {
      console.error("appendToPage tool called");
      try {
        await ensureGraphClient();
        
        const pageId = params.page_id;
        const content = params.content;
        const target = params.target || 'body';
        
        // Build the PATCH request body
        const patchCommands = [
          {
            target: target,
            action: "append",
            position: "after",
            content: content
          }
        ];
        
        const url = `https://graph.microsoft.com/v1.0/me/onenote/pages/${pageId}/content`;
        console.error("Appending content to:", url);
        
        const token = await getAccessToken();
        const response = await fetch(url, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(patchCommands)
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}. Details: ${errorText}`);
        }
        
        console.error("Content appended successfully");
        
        return { 
          content: [
            {
              type: "text",
              text: JSON.stringify({ 
                success: true, 
                message: "Content appended successfully",
                pageId: pageId
              })
            }
          ]
        };
      } catch (error) {
        console.error("Error appending to page:", error);
        throw new Error(`Failed to append to page: ${error.message}`);
      }
    }
  );

  return server;
}
