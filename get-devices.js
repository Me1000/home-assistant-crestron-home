const https = require('https');
const fs = require('fs');

const WEB_API_TOKEN = 'C6p5Mtp57LCP';
const BASE_URL = 'https://10.1.1.40/cws/api';

async function makeRequest(path, headers = {}, method = "GET") {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE_URL + path);
    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method,
      headers,
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
    console.log('Getting sensors list...');
    const response = await makeRequest('/sensors', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Sensors list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get sensors: ${error.message}`);
  }
}

async function getRooms(authKey) {
  try {
    console.log('Getting rooms list...');
    const response = await makeRequest('/rooms', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Rooms list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get rooms: ${error.message}`);
  }
}

async function getScenes(authKey) {
  try {
    console.log('Getting scenes list...');
    const response = await makeRequest('/scenes', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Scenes list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get scenes: ${error.message}`);
  }
}

async function getSecurityDevices(authKey)
{
  try {
    console.log('Getting Security devices list...');
    const response = await makeRequest('/securitydevices', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Security devices list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get Security devices: ${error.message}`);
  }
}

async function getMediaRooms(authKey)
{
  try {
    console.log('Getting Media Room list...');
    const response = await makeRequest('/mediarooms', {
      'Crestron-RestAPI-AuthKey': authKey
    });
    
    console.log('✓ Media rooms list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get media rooms: ${error.message}`);
  }
}

async function playInLivingRoom(authKey)
{
  // https://10.1.1.40/cws/api/mediaroom/1003/selectsource/53750
  try {
    console.log("Set living room media source to Sonos");
    const response = await makeRequest("/mediarooms/1006/selectsource/53750", {
      "Crestron-RestAPI-AuthKey": authKey
    }, "POST");
    
    console.log('✓ Media rooms list retrieved');
    return response;
  } catch (error) {
    throw new Error(`Failed to get media rooms: ${error.message}`);
  }
}

async function main() {
  try {
    console.log(`Connecting to Crestron Home at ${BASE_URL}...`);
    
    const authKey = await getAuthKey();
    
    // Fetch all data in parallel
    const [ devices, sensors, rooms, scenes, securityDevices, mediaRooms, playAction ] = await Promise.all([
      getDevices(authKey),
      getSensors(authKey),
      getRooms(authKey),
      getScenes(authKey),
      getSecurityDevices(authKey),
      getMediaRooms(authKey),
      playInLivingRoom(authKey),
    ]);
    
    // Combine all data into a single object
    const allData = {
      devices,
      sensors,
      rooms,
      scenes,
      securityDevices,
      mediaRooms,
      playAction,
      timestamp: new Date().toISOString(),
    };
    
    console.log('\n📱 Complete Crestron Home Data:');
    console.log(JSON.stringify(allData, null, 2));
    
    // Log summary counts
    if (devices.devices && Array.isArray(devices.devices)) {
      console.log(`\n📊 Total devices found: ${devices.devices.length}`);
    }
    if (sensors.devices && Array.isArray(sensors.devices)) {
      console.log(`📊 Total sensors found: ${sensors.devices.length}`);
    }
    if (rooms.rooms && Array.isArray(rooms.rooms)) {
      console.log(`📊 Total rooms found: ${rooms.rooms.length}`);
    }
    if (scenes.scenes && Array.isArray(scenes.scenes)) {
      console.log(`📊 Total scenes found: ${scenes.scenes.length}`);
    }
    
    // Write all data to JSON file
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `crestron-home-data-${timestamp}.json`;
    
    fs.writeFileSync(filename, JSON.stringify(allData, null, 2));
    console.log(`\n💾 All data saved to: ${filename}`);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { getAuthKey, getDevices, getSensors, getRooms, getScenes };