# FaceIt Frontend

## Setup

1. Install dependencies

   ```bash
   npm install
   ```

2. Create a `.env` file with your API base URL:

   ```bash
   # For physical device testing, use your computer's local IPv4 address
   # Find it with: ipconfig getifaddr en0 (macOS)
   EXPO_PUBLIC_API_URL=http://192.168.x.x:8000

   # For simulator/emulator only, you can use localhost
   # EXPO_PUBLIC_API_URL=http://localhost:8000
   ```

   > **Note:** Your iPhone must be on the same Wi-Fi network as your computer to reach the API.

## Running the App

Make sure the backend server is running. Navigate to `../backend` and run the following command in a different terminal:

```bash
   uvicorn app.main:app --host 0.0.0.0 --reload
```

Then, in the `frontend/` (this directory), run:

```bash
npx expo start
```

Then press:
- `i` — iOS simulator
- `a` — Android emulator
- Scan QR code — Expo Go on physical device
