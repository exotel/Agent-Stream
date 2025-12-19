#!/usr/bin/env node
/**
 * Make a test call using Exotel API
 * 
 * Usage:
 *   node scripts/make-call.js <phone-number>
 *   node scripts/make-call.js +91XXXXXXXXXX
 */

require('dotenv').config();
const ExotelApi = require('../src/utils/exotelApi');

const customerPhone = process.argv[2];

if (!customerPhone) {
  console.log(`
Usage: node scripts/make-call.js <phone-number>

Example:
  node scripts/make-call.js +91XXXXXXXXXX

Environment variables required:
  EXOTEL_API_KEY       - Exotel API Key
  EXOTEL_API_TOKEN     - Exotel API Token  
  EXOTEL_ACCOUNT_SID   - Exotel Account SID
  EXOTEL_VIRTUAL_NUMBER - Exotel Virtual Number
  EXOTEL_FLOW_ID       - Exotel Flow ID
`);
  process.exit(1);
}

async function makeCall() {
  const exotel = new ExotelApi();
  
  const virtualNumber = process.env.EXOTEL_VIRTUAL_NUMBER;
  const flowId = process.env.EXOTEL_FLOW_ID;
  
  // Get WSS URL from ngrok or use local
  let wssUrl = process.env.WSS_URL;
  
  if (!wssUrl) {
    try {
      // Try to get ngrok URL
      const http = require('http');
      const response = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:4040/api/tunnels', (res) => {
          let data = '';
          res.on('data', chunk => data += chunk);
          res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
      });
      
      const tunnel = response.tunnels.find(t => t.public_url.startsWith('https'));
      if (tunnel) {
        wssUrl = tunnel.public_url.replace('https', 'wss') + '/media';
      }
    } catch (e) {
      console.log('⚠️  Could not detect ngrok URL');
    }
  }
  
  console.log('═══════════════════════════════════════════════════════');
  console.log('📞 Making Exotel Call');
  console.log('═══════════════════════════════════════════════════════');
  console.log(`   Customer: ${customerPhone}`);
  console.log(`   Virtual Number: ${virtualNumber}`);
  console.log(`   Flow ID: ${flowId}`);
  console.log(`   WSS URL: ${wssUrl || 'Not configured'}`);
  console.log('═══════════════════════════════════════════════════════');
  
  try {
    // Use base flow URL (wss_url should be configured in Exotel flow)
    const flowUrl = `http://my.exotel.com/${process.env.EXOTEL_ACCOUNT_SID}/exoml/start_voice/${flowId}`;
    
    const call = await exotel.makeCall({
      from: customerPhone,
      to: virtualNumber,
      callerId: virtualNumber,
      flowUrl: flowUrl
    });
    
    console.log(`   WSS should be configured in flow: ${wssUrl || 'Update in Exotel dashboard'}`);
    
    console.log('');
    console.log('✅ Call initiated successfully!');
    console.log(`   Call SID: ${call.Sid}`);
    console.log(`   Status: ${call.Status}`);
    console.log('');
    console.log('📞 Answer your phone!');
    
  } catch (error) {
    console.error('❌ Failed to make call:', error.message);
    process.exit(1);
  }
}

makeCall();

