import { PublicClientApplication } from '@azure/msal-node';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const tokenFilePath = path.join(__dirname, '.access-token.txt');
const cacheFilePath = path.join(__dirname, '.msal-cache.json');

const clientId = '14d82eec-204b-4c2f-b7e8-296a70dab67e';
const scopes = ['Notes.Read.All', 'Notes.ReadWrite.All', 'User.Read', 'offline_access'];

// Clear the cache file to force new login
if (fs.existsSync(cacheFilePath)) {
  fs.unlinkSync(cacheFilePath);
  console.log('Cleared existing token cache');
}

const msalConfig = {
  auth: {
    clientId: clientId,
    authority: 'https://login.microsoftonline.com/common'
  }
};

const pca = new PublicClientApplication(msalConfig);

async function authenticate() {
  try {
    console.log('Starting authentication...');
    console.log('You will see a URL and code to enter shortly...');
    console.log('(Use incognito browser to login with a different account)\n');

    const deviceCodeRequest = {
      scopes: scopes,
      deviceCodeCallback: (response) => {
        console.log(response.message);
      }
    };

    const response = await pca.acquireTokenByDeviceCode(deviceCodeRequest);
    
    // Save access token
    fs.writeFileSync(tokenFilePath, JSON.stringify({ token: response.accessToken }));
    
    // Save the cache (includes refresh token)
    const cache = pca.getTokenCache().serialize();
    fs.writeFileSync(cacheFilePath, cache);
    
    console.log('\nAuthentication successful!');
    console.log('Access token saved to:', tokenFilePath);
    console.log('Cache saved to:', cacheFilePath);
    console.log('Token expires:', response.expiresOn.toLocaleString());
    
  } catch (error) {
    console.error('Authentication error:', error.message);
  }
}

authenticate();
