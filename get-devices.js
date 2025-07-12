const https = require('https');
const fs = require('fs');

const WEB_API_TOKEN = '';
const BASE_URL = 'https://10.1.1.40/cws/api';

async function makeRequest(path, headers = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE_URL + path);
    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'GET',
      headers: headers,
      rejectUnauthorized: false // Skip SSL certificate validation for local devices
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const jsonData = JSON.parse(data);
          resolve(jsonData);
        } catch (e) {
          reject(new Error(`Invalid JSON response: ${data}`));
        }
      });
    });

    req.on('error', (err) => {
      reject(err);
    });

    req.end();
  });
}

async function getAuthKey() {
  try {
    console.log('Getting auth key...');
    const response = await makeRequest('/login', {
      'Crestron-RestAPI-AuthToken': WEB_API_TOKEN
    });
    
    if (response.authkey) {
      console.log('✓ Auth key obtained');
      return response.authkey;
    } else {
      throw new Error('No auth key in response');
    }
  } catch (error) {
    throw new Error(`Failed to get auth key: ${error.message}`);
  }
}

async function getDevices(authKey) {
  try {
    console.log('Getting device list...');
    const response = await makeRequest('/devices', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Device list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get devices: ${error.message}`);
  }
}

async function getSensors(authKey) {
  try {
    console.log('Getting device list...');
    const response = await makeRequest('/sensors', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Sensors list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get sensors: ${error.message}`);
  }
}

async function main() {
  try {
    console.log(`Connecting to Crestron Home at ${BASE_URL}...`);
    
    const authKey = await getAuthKey();
    const devices = await getSensors(authKey);
    
    console.log('\n📱 Devices:');
    console.log(JSON.stringify(devices, null, 2));
    
    if (devices.devices && Array.isArray(devices.devices)) {
      console.log(`\n📊 Total devices found: ${devices.devices.length}`);
    }
    
    // Write devices to JSON file
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `devices-${timestamp}.json`;
    
    fs.writeFileSync(filename, JSON.stringify(devices, null, 2));
    console.log(`\n💾 Devices saved to: ${filename}`);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { getAuthKey, getDevices };