import { PublicClientApplication } from '@azure/msal-node';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const clientId = '14d82eec-204b-4c2f-b7e8-296a70dab67e';
const scopes = ['Notes.Read.All', 'Notes.ReadWrite.All', 'User.Read', 'offline_access'];
const cacheFilePath = path.join(__dirname, '.msal-cache.json');

const msalConfig = {
  auth: {
    clientId: clientId,
    authority: 'https://login.microsoftonline.com/common'
  }
};

const pca = new PublicClientApplication(msalConfig);

// Load cache from file
if (fs.existsSync(cacheFilePath)) {
  pca.getTokenCache().deserialize(fs.readFileSync(cacheFilePath, 'utf8'));
  console.log('Cache loaded from:', cacheFilePath);
} else {
  console.log('❌ No cache file found. Run: npm run auth');
  process.exit(1);
}

async function checkStatus() {
  const accounts = await pca.getTokenCache().getAllAccounts();
  
  if (accounts.length === 0) {
    console.log('❌ No cached accounts. Run: npm run auth');
    return;
  }
  
  console.log('Account:', accounts[0].username);
  
  try {
    const response = await pca.acquireTokenSilent({
      account: accounts[0],
      scopes: scopes
    });
    
    const expiresOn = response.expiresOn;
    const mins = Math.round((expiresOn - new Date()) / 60000);
    console.log('✅ Token valid | Expires:', expiresOn.toLocaleString(), `(${mins} min)`);
    
    // Save updated cache
    fs.writeFileSync(cacheFilePath, pca.getTokenCache().serialize());
  } catch (error) {
    console.log('❌ Token refresh failed:', error.message);
    console.log('Run: npm run auth');
  }
}

checkStatus();
