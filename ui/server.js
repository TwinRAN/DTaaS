const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const config = require('./config');
require('dotenv').config();

const app = express();
const PORT = config.server.port;
const HOST = config.server.host;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Read token from secret file
function getInfluxToken() {
    try {
        return fs.readFileSync(config.influxdb.tokenFile, 'utf8').trim();
    } catch (error) {
        console.error('Error reading InfluxDB token:', error);
        return process.env.INFLUXDB_TOKEN || '';
    }
}

// Proxy endpoint for InfluxDB queries
app.post('/api/v2/query', async (req, res) => {
    try {
        const { query } = req.body;
        const token = getInfluxToken();
        
        if (!token) {
            return res.status(500).json({ error: 'InfluxDB token not configured' });
        }

        const response = await fetch(`${config.influxdb.url}/api/v2/query?org=${config.influxdb.org}&bucket=${config.influxdb.bucket}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/vnd.flux',
                'Authorization': `Token ${token}`
            },
            body: query
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('InfluxDB error:', response.status, errorText);
            return res.status(response.status).json({ 
                error: `InfluxDB error: ${response.status}`,
                details: errorText
            });
        }

        const data = await response.text();
        res.set('Content-Type', 'text/plain');
        res.send(data);

    } catch (error) {
        console.error('Proxy error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        timestamp: new Date().toISOString(),
        config: {
            influxdb: {
                url: config.influxdb.url,
                org: config.influxdb.org,
                bucket: config.influxdb.bucket
            }
        }
    });
});

// Configuration endpoint for frontend
app.get('/api/config', (req, res) => {
    res.json({
        influxdb: {
            bucket: config.influxdb.bucket,
            org: config.influxdb.org
        }
    });
});

// Proxy endpoints for aiaas
app.get('/api/models', async (req, res) => {
    try {
        const response = await fetch('http://aiaas:8000/models');
        
        if (!response.ok) {
            return res.status(response.status).json({ 
                error: `Model API error: ${response.status}`,
                details: await response.text()
            });
        }

        const data = await response.json();
        res.json(data);

    } catch (error) {
        console.error('Model API proxy error:', error);
        res.status(500).json({ error: 'Failed to fetch models from aiaas' });
    }
});

app.post('/api/predict', async (req, res) => {
    try {
        const response = await fetch('http://aiaas:8000/api/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(req.body)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            return res.status(response.status).json({ 
                error: `Model API error: ${response.status}`,
                details: errorText
            });
        }

        const data = await response.json();
        res.json(data);

    } catch (error) {
        console.error('Model API proxy error:', error);
        res.status(500).json({ error: 'Failed to get prediction from aiaas' });
    }
});

// Debug endpoint to see what data exists
app.get('/api/debug', async (req, res) => {
    try {
        const token = getInfluxToken();
        
        if (!token) {
            return res.status(500).json({ error: 'InfluxDB token not configured' });
        }

        // Simple query to see what measurements exist
        const query = `
            from(bucket: "${config.influxdb.bucket}")
                |> range(start: -1h)
                |> limit(n: 10)
        `;

        const response = await fetch(`${config.influxdb.url}/api/v2/query?org=${config.influxdb.org}&bucket=${config.influxdb.bucket}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/vnd.flux',
                'Authorization': `Token ${token}`
            },
            body: query
        });

        if (!response.ok) {
            const errorText = await response.text();
            return res.status(response.status).json({ 
                error: `InfluxDB error: ${response.status}`,
                details: errorText
            });
        }

        const data = await response.text();
        res.set('Content-Type', 'text/plain');
        res.send(data);

    } catch (error) {
        console.error('Debug error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Serve the main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something broke!' });
});

// Start server
app.listen(PORT, HOST, () => {
    console.log(`TwinRAN UI server running on http://${HOST}:${PORT}`);
    console.log(`InfluxDB URL: ${config.influxdb.url}`);
    console.log(`InfluxDB Org: ${config.influxdb.org}`);
    console.log(`InfluxDB Bucket: ${config.influxdb.bucket}`);
}); 