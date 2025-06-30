// TwinRAN UI Configuration

const config = {
    // Server configuration
    server: {
        port: process.env.UI_PORT || 3000,
        host: process.env.UI_HOST || '0.0.0.0'
    },

    // InfluxDB configuration
    influxdb: {
        url: process.env.INFLUXDB_URL || 'http://localhost:8086',
        org: process.env.INFLUXDB_ORG || 'twinran',
        bucket: process.env.INFLUXDB_BUCKET || 'xapp',
        tokenFile: process.env.INFLUXDB_TOKEN_FILE || '../secrets/influxdb_token'
    },

    // UI configuration
    ui: {
        autoRefreshInterval: 30000, // 30 seconds
        defaultTimeRange: '1h',
        maxDataPoints: 1000,
        chartColors: {
            primary: '#3498db',
            secondary: '#e74c3c',
            background: 'rgba(52, 152, 219, 0.1)'
        }
    },

    // Time ranges available in the UI
    timeRanges: [
        { value: '1h', label: 'Last Hour' },
        { value: '6h', label: 'Last 6 Hours' },
        { value: '24h', label: 'Last 24 Hours' },
        { value: '7d', label: 'Last 7 Days' }
    ]
};

module.exports = config; 