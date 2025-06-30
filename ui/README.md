# TwinRAN Network Topology Viewer

A modern web-based UI for visualizing TwinRAN network topology, displaying UEs and gNodeBs with real-time data from InfluxDB.

## Features

- **Interactive Topology Visualization**: Force-directed graph showing UEs and gNodeBs
- **Real-time Data**: Fetches latest data from InfluxDB with configurable time ranges
- **Node Information**: Hover over nodes to see detailed data in tabular format
- **Time Series View**: Click on UE nodes to view historical data in a popup chart
- **Auto-refresh**: Automatically updates data every 30 seconds
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

- Node.js (v14 or higher)
- InfluxDB running with KPM data
- Access to InfluxDB token

## Installation

1. Navigate to the UI directory:
   ```bash
   cd ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables (optional):
   Create a `.env` file in the UI directory:
   ```env
   UI_PORT=3000
   INFLUXDB_URL=http://localhost:8086
   INFLUXDB_ORG=twinran
   INFLUXDB_BUCKET=kpm_data
   INFLUXDB_TOKEN_FILE=../secrets/influxdb_token
   ```

## Usage

1. Start the UI server:
   ```bash
   npm start
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

3. The topology viewer will automatically load and display:
   - **Red nodes**: gNodeBs (base stations)
   - **Blue nodes**: UEs (user equipment)
   - **Gray lines**: Connections between UEs and gNodeBs

## Interaction

- **Hover over nodes**: Shows detailed information in the sidebar
- **Click on UE nodes**: Opens a time series chart popup
- **Drag nodes**: Reposition nodes in the visualization
- **Refresh button**: Manually refresh data
- **Time range selector**: Choose different time periods for data

## Data Format

The UI expects InfluxDB data with the following structure:
- Measurement: `kpm_measurement`
- Tags: `ue_id`, `gnb_id`
- Fields: Various KPM metrics

## Troubleshooting

### Connection Issues
- Ensure InfluxDB is running and accessible
- Check that the token file exists and is readable
- Verify the InfluxDB URL, org, and bucket settings

### No Data Displayed
- Check browser console for error messages
- Verify that KPM data is being written to InfluxDB
- Ensure the data format matches expected structure

### CORS Errors
- The UI server acts as a proxy to avoid CORS issues
- If you see CORS errors, ensure the proxy is working correctly

## Development

To run in development mode:
```bash
npm run dev
```

The UI uses:
- **D3.js**: For force-directed graph visualization
- **Chart.js**: For time series charts
- **Express.js**: For the web server and InfluxDB proxy

## API Endpoints

- `GET /`: Main UI page
- `POST /api/v2/query`: Proxy endpoint for InfluxDB queries
- `GET /health`: Health check endpoint

## License

MIT License 