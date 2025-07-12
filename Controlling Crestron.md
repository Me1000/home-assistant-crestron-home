This guide assumes you’ve already generated a **Web API Authentication Token** in the Crestron Home setup app; you’ll use that token to obtain a short-lived **AuthKey**, which in turn is required on every subsequent request.

## Authentication

### 1. Generate the Web API Token

In the Crestron Home setup app, go to **Installer Settings → System Control Options → Web API Settings**, then tap **Update Token** to produce a new token and save it.

### 2. Exchange for an AuthKey

Send your web API token in a GET to `/cws/api/login`:

```http
GET https://<HOST>/cws/api/login
Crestron-RestAPI-AuthToken: <your-API-token>
```

On success you get JSON with an opaque `authkey` value. Include that value as `Crestron-RestAPI-AuthKey` in all future requests ([sdkcon78221.crestron.com][2]).

## Listing Lights

### GET `/cws/api/lights`

Retrieve every lighting load in one call:

```http
GET https://<HOST>/cws/api/lights
Crestron-RestAPI-AuthKey: <your-authkey>
```

#### Sample Response

```json
{
  "lights": [
    {
      "level": 0,
      "id": 1060,
      "name": "Downlight",
      "subType": "Dimmer",
      "connectionStatus": "online",
      "roomId": 1058
    },
    {
      "level": 0,
      "id": 1065,
      "name": "Accent",
      "subType": "Dimmer",
      "connectionStatus": "online",
      "roomId": 1058
    },
    {
      "level": 0,
      "id": 1068,
      "name": "Pendant",
      "subType": "Switch",
      "connectionStatus": "online",
      "roomId": 1058
    }
  ],
  "version": "2.000.0004"
}
```

([sdkcon78221.crestron.com][3], [sdkcon78221.crestron.com][4])

* **`id`**: unique light identifier
* **`subType`**: `dimmer` supports variable `level` (0–65535); `switch` is on/off only ([sdkcon78221.crestron.com][4])
* **`level`**: current brightness (0 = off, 65535 = full)
* **`roomId`**: lets you group lights by physical area

You can also GET a single light with `/cws/api/lights/{id}` using the same header ([sdkcon78221.crestron.com][3]).

## Listing Sensors

### GET `/cws/api/sensors`

Fetch all sensor devices—photo sensors, occupancy sensors, door sensors, etc.—in one request:

```http
GET https://<HOST>/cws/api/sensors
Crestron-RestAPI-AuthKey: <your-authkey>
```

#### Sample Response

```json
{
  "sensors": [
    {
      "id": 7,
      "name": "Hallway Occupancy",
      "subType": "OccupancySensor",
      "presence": "Vacant",
      "roomId": 2
    },
    {
      "id": 11,
      "name": "Front Porch Light Sensor",
      "subType": "PhotoSensor",
      "level": 128,
      "connectionStatus": "online",
      "presence": "Occupied",
      "roomId": 5
    }
  ],
  "version": "2.000.0004"
}
```

([sdkcon78221.crestron.com][5], [sdkcon78221.crestron.com][4])

* **`subType`**: distinguishes sensor kind; occupancy sensors report `"presence"` (`Occupied`/`Vacant`/`Unavailable`) ([sdkcon78221.crestron.com][4])
* **`level`**: for photo sensors only (0–255)
* **GET `/sensors/{id}`** works similarly if you only care about one sensor ([sdkcon78221.crestron.com][5]).

## Setting Light Brightness

### POST `/cws/api/lights/SetState`

Change one or more light levels in a single call:

```http
POST https://<HOST>/cws/api/lights/SetState
Content-Type: application/json
Crestron-RestAPI-AuthKey: <your-authkey>

{
  "lights": [
    { "id": 10, "level": 65535, "time": 0 },
    { "id": 12, "level": 0,     "time": 500 }
  ]
}
```

* **`level`**: 0–65535
* **`time`**: fade duration in milliseconds (0 = immediate)
* The server responds with `status: "success"` or details of any failures ([sdkcon78221.crestron.com][3], [sdkcon78221.crestron.com][6]).

### Dimmers vs Switches

* **Dimmer** (`subType: "dimmer"`) honors any level between 0 and 65535, enabling smooth fades.
* **Switch** (`subType: "switch"`) treats any non-zero `level` as “on” at full brightness (65535), ignoring intermediate values ([sdkcon78221.crestron.com][4]).

## Examples & Community Tools

A number of community plugins (e.g., [homebridge-crestron-home](https://github.com/evgolsh/homebridge-crestron-home)) demonstrate this same pattern in Node.js—storing your token, logging in every 9 minutes, polling devices, and issuing SetState calls for lights ([GitHub][7]). Similarly, the [npope home-assistant-crestron-component](https://github.com/npope/home-assistant-crestron-component) registers Crestron lights and sensors as entities using these exact endpoints ([GitHub][8]).

---

With this in hand—AuthToken → AuthKey, GET `/lights` and `/sensors`, and POST `/lights/SetState`—you have everything needed to build a full Crestron Home integration (for lights and sensors) in any programming language or framework.

[1]: https://sdkcon78221.crestron.com/sdk/Crestron-Home-API/Content/Topics/Quick-Start/Overview.htm?utm_source=chatgpt.com "Overview | REST API for Crestron Home® OS Manual"
[2]: https://sdkcon78221.crestron.com/sdk/Crestron-Home-API/Content/Topics/API-Reference/Login-API.htm?utm_source=chatgpt.com "Login API | REST API for Crestron Home® OS Manual"
[3]: https://sdkcon78221.crestron.com/sdk/Crestron-Home-API/Content/Topics/API-Reference/Lights-API.htm "Lights API | REST API for Crestron Home® OS Manual"
[4]: https://sdkcon78221.crestron.com/sdk/Crestron-Home-API/Content/Topics/API-Reference/JSON-Payload-Fields.htm?utm_source=chatgpt.com "JSON Payload Fields - Crestron Electronics"
[5]: https://sdkcon78221.crestron.com/sdk/Crestron-Home-API/Content/Topics/API-Reference/Sensors-API.htm "Sensors API | REST API for Crestron Home® OS Manual"
[6]: https://sdkcon78221.crestron.com/sdk/Crestron-Home-API/Content/Topics/API-Reference/Lights-API.htm?utm_source=chatgpt.com "Lights API | REST API for Crestron Home® OS Manual"
[7]: https://github.com/evgolsh/homebridge-crestron-home?utm_source=chatgpt.com "Homebridge plugin for Crestron Home - GitHub"
[8]: https://github.com/npope/home-assistant-crestron-component?utm_source=chatgpt.com "npope/home-assistant-crestron-component - GitHub"
