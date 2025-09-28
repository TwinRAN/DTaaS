class TwinRANTopology {
    constructor() {
        this.nodes = [];
        this.links = [];
        this.simulation = null;
        this.svg = null;
        this.width = 0;
        this.height = 0;
        this.config = null;
        this.timeSeriesChart = null;
        this.currentTimeSeriesData = null;
        
        this.init();
    }

    async init() {
        await this.loadConfig();
        this.setupEventListeners();
        this.setupModal();
        this.loadData();
        this.setupAutoRefresh();
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.config = await response.json();
        } catch (error) {
            console.error('Error loading configuration:', error);
            // Fallback to default configuration
            this.config = {
                influxdb: {
                    bucket: 'xapp',
                    org: 'BTS'
                }
            };
        }
    }

    setupEventListeners() {
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadData();
        });

        document.getElementById('debugBtn').addEventListener('click', () => {
            this.debugData();
        });

        document.getElementById('timeRange').addEventListener('change', () => {
            this.loadData();
        });

        // Modal close events
        document.querySelector('.close').addEventListener('click', () => {
            this.hideModal();
        });

        window.addEventListener('click', (event) => {
            const modal = document.getElementById('timeSeriesModal');
            if (event.target === modal) {
                this.hideModal();
            }
        });
    }

    setupModal() {
        // Modal functionality is handled in the event listeners
    }

    async loadData() {
        try {
            const timeRange = document.getElementById('timeRange').value;
            console.log('Loading data for time range:', timeRange);
            const data = await this.fetchInfluxData(timeRange);
            console.log('Raw data from InfluxDB:', data);
            this.processData(data);
            console.log('Processed nodes:', this.nodes);
            console.log('Processed links:', this.links);
            this.renderTopology();
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data from InfluxDB');
        }
    }

    async fetchInfluxData(timeRange) {
        // Query to get latest data for each UE-gNB combination with all fields
        const query = `
            from(bucket: "${this.config.influxdb.bucket}")
                |> range(start: ${this.getTimeRangeStart(timeRange)}, stop: now())
                |> filter(fn: (r) => exists r.gnb_id and exists r.ue_id)
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> map(fn: (r) => ({ r with combo: r.gnb_id + ":" + r.ue_id }))
                |> group(columns: ["ue_id", "gnb_id"])
                |> last(column: "_time")
        `;

        const response = await fetch('/api/v2/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.text();
        return this.parseFluxResponse(data);
    }

    getTimeRangeStart(timeRange) {
        const now = new Date();
        switch (timeRange) {
            case '1h':
                return new Date(now.getTime() - 60 * 60 * 1000).toISOString();
            case '6h':
                return new Date(now.getTime() - 6 * 60 * 60 * 1000).toISOString();
            case '24h':
                return new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
            case '7d':
                return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
            default:
                return new Date(now.getTime() - 60 * 60 * 1000).toISOString();
        }
    }

    getInfluxToken() {
        // Token is now handled by the server proxy
        return null;
    }

    parseFluxResponse(fluxData) {
        const lines = fluxData.split('\n');
        const data = [];
        
        // Skip header lines
        let dataStarted = false;
        let headerLine = null;
        
        for (const line of lines) {
            console.log('Processing line:', line);
            if (line.startsWith('#') || line.trim() === '') continue;
            
            // Check if this is the data header line
            if (line.includes('_time') || line.includes('ue_id')) {
                dataStarted = true;
                headerLine = line;
                console.log('Found header line:', headerLine);
                continue;
            }
            
            if (!dataStarted) continue;
            
            const parts = line.split(',');
            if (parts.length < 3) continue;
            
            try {
                // Parse the Flux CSV format with pivoted data
                const headers = headerLine.split(',');
                console.log('Headers:', headers);
                
                const record = {};
                
                // Map each column to its value
                headers.forEach((header, index) => {
                    const value = parts[index] || '';
                    const cleanHeader = header.trim();
                    
                    // Convert numeric fields to numbers
                    if (cleanHeader.includes('_time') || cleanHeader.includes('timestamp')) {
                        record.timestamp = value;
                    } else if (cleanHeader === 'ue_id') {
                        record.ue_id = value;
                    } else if (cleanHeader === 'gnb_id') {
                        record.gnb_id = value;
                    } else if (cleanHeader === 'combo') {
                        record.combo = value;
                    } else if (cleanHeader.includes('_field') || cleanHeader.includes('_measurement')) {
                        // Skip these columns
                        return;
                    } else {
                        // This is a data field (like throughput_dl_kbps, rsrp, etc.)
                        const numericValue = parseFloat(value);
                        record[cleanHeader] = isNaN(numericValue) ? value : numericValue;
                    }
                });
                
                console.log('Parsed record:', record);
                data.push(record);
            } catch (e) {
                console.warn('Failed to parse line:', line, e);
            }
        }
        
        console.log('Total parsed records:', data.length);
        return data;
    }

    processData(data) {
        this.nodes = [];
        this.links = [];
        
        const ueMap = new Map();
        const gnbMap = new Map();
        
        // Process data to extract UEs and gNBs
        data.forEach(record => {
            const ueId = record.ue_id;
            const gnbId = record.gnb_id;
            
            // Check if gNB object exists, if not create it
            if (gnbId && !gnbMap.has(gnbId)) {
                gnbMap.set(gnbId, {
                    id: gnbId,
                    type: 'gnb',
                    data: { 
                        gnb_id: gnbId, 
                        name: `Base Station ${gnbId}`,
                        type: 'gNodeB',
                        status: 'Active'
                    },
                    size: 35
                });
            }
            
            // Create composite key for UE (ue_id + gnb_id) since ue_id can be same across different gNBs
            const compositeUeKey = `${ueId}_${gnbId}`;
            
            // Add UE if not exists (using composite key)
            if (!ueMap.has(compositeUeKey)) {
                ueMap.set(compositeUeKey, {
                    id: compositeUeKey, // Use composite key as unique ID
                    displayId: ueId, // Keep original UE ID for display
                    type: 'ue',
                    data: record,
                    gnb: gnbId // Attach to the specific gNodeB from data
                });
            }
        });
        
        // Convert gNBs to nodes
        const gnbNodes = Array.from(gnbMap.values());
        
        // Convert UEs to nodes
        const ueNodes = Array.from(ueMap.values()).map(ue => ({
            id: ue.id, // Use composite key for unique identification
            displayId: ue.displayId, // Original UE ID for display
            type: 'ue',
            data: ue.data,
            size: 25
        }));
        
        // Create links from each UE to its parent gNB
        const links = ueNodes.map(ue => ({
            source: ue.data.gnb_id,
            target: ue.id
        })).filter(link => link.source); // Filter out any UEs without gnb_id
        
        this.nodes = [...gnbNodes, ...ueNodes];
        this.links = links;
    }

    renderTopology() {
        const container = document.getElementById('topology');
        this.width = container.clientWidth;
        this.height = container.clientHeight;
        
        // Clear existing content
        container.innerHTML = '';
        
        // Create SVG
        this.svg = d3.select('#topology')
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height)
            .on('click', () => {
                // Clear selection when clicking on empty space
                this.svg.selectAll('.node').classed('selected', false);
                this.hideNodeInfo();
            });
        
        // Create force simulation
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => d.size + 5));
        
        // Create links
        const link = this.svg.append('g')
            .selectAll('line')
            .data(this.links)
            .enter().append('line')
            .attr('class', 'link');
        
        // Create nodes
        const node = this.svg.append('g')
            .selectAll('g')
            .data(this.nodes)
            .enter().append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', this.dragstarted.bind(this))
                .on('drag', this.dragged.bind(this))
                .on('end', this.dragended.bind(this)));
        
        // Add circles to nodes
        node.append('circle')
            .attr('r', d => d.size)
            .attr('class', d => d.type);
        
        // Add labels to nodes
        node.append('text')
            .text(d => {
                let displayText;
                if (d.type === 'ue') {
                    // For UE nodes, show "UE" prefix with original UE ID
                    displayText = `UE ${d.displayId}`;
                } else if (d.type === 'gnb') {
                    // For gNB nodes, show "gNB" prefix with gNB ID
                    displayText = `gNB ${d.id}`;
                } else {
                    // Fallback for other node types
                    displayText = d.id;
                }
                
                // Truncate if too long
                return displayText.length > 12 ? displayText.substring(0, 12) + '...' : displayText;
            });
        
        // Add event listeners
        node.on('click', (event, d) => {
            event.stopPropagation(); // Prevent event from bubbling to SVG
            // Remove previous selection
            this.svg.selectAll('.node').classed('selected', false);
            // Add selection to clicked node
            d3.select(event.currentTarget).classed('selected', true);
            this.showNodeInfo(event, d);
        });
        
        // Update positions on simulation tick
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    showNodeInfo(event, d) {
        const nodeInfo = document.getElementById('nodeInfo');
        const nodeDetails = document.getElementById('nodeDetails');
        
        // Update the header to show node type
        const header = nodeInfo.querySelector('h3');
        if (d.type === 'gnb') {
            header.textContent = 'gNodeB Information';
        } else if (d.type === 'ue') {
            header.textContent = 'UE Information';
        } else {
            header.textContent = 'Node Information';
        }
        
        // Create table with node data
        const table = this.createDataTable(d.data);
        nodeDetails.innerHTML = '';
        nodeDetails.appendChild(table);
        
        // Add metrics button for UEs
        if (d.type === 'ue') {
            const metricsButton = document.createElement('button');
            metricsButton.textContent = 'Show Metrics';
            metricsButton.className = 'metrics-btn';
            metricsButton.onclick = () => this.showTimeSeries(event, d);
            nodeDetails.appendChild(metricsButton);
            
            // Add current downlink throughput display using existing data
            const throughputDiv = document.createElement('div');
            throughputDiv.className = 'throughput-display';
            
            // Get throughput from existing data - look for throughput_dl_kbps field
            console.log('UE data fields:', Object.keys(d.data));
            console.log('UE data:', d.data);
            const throughputValue = d.data['throughput_dl_kbps'] || 0;
            const throughputInMbps = (throughputValue / 1000).toFixed(2); // Convert kbps to Mbps
            console.log('Throughput value:', throughputValue);
            console.log('Throughput in Mbps:', throughputInMbps);
            
            throughputDiv.innerHTML = `
                <h4>Current Downlink Throughput</h4>
                <div class="throughput-value ${throughputValue >= 0 ? 'success' : 'error'}">
                    ${throughputValue >= 0 ? `${throughputInMbps} Mbps` : 'No data available'}
                </div>
            `;
            nodeDetails.appendChild(throughputDiv);
        }
        
        nodeInfo.classList.remove('hidden');
    }

    hideNodeInfo() {
        document.getElementById('nodeInfo').classList.add('hidden');
    }


    createDataTable(data) {
        const table = document.createElement('table');
        table.className = 'node-details';
        
        const tbody = document.createElement('tbody');
        
        // Define metadata fields to show (exclude metric fields)
        const metadataFields = ['ue_id', 'gnb_id', 'timestamp'];
        
        Object.entries(data).forEach(([key, value]) => {
            
            // Only show metadata fields
            if (!metadataFields.includes(key)) {
                return;
            }
            
            // Rename timestamp to last heartbeat timestamp
            if (key === 'timestamp') {
                key = 'last heartbeat timestamp';
                value = new Date(value).toLocaleString();
            }
            
            // Rename gnb_id to gNB ID for better display
            if (key === 'gnb_id') {
                key = 'gNB ID';
            }
            
            // Rename ue_id to UE ID for better display
            if (key === 'ue_id') {
                key = 'UE ID';
            }
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <th>${key}</th>
                <td>${value}</td>
            `;
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        return table;
    }

    async showTimeSeries(event, d) {
        if (d.type !== 'ue') return;
        
        try {
            // For UE nodes, use the original UE ID for time series queries, not the composite key
            const originalUeId = d.displayId || d.data.ue_id;
            console.log('Fetching time series for UE:', originalUeId);
            const timeSeriesData = await this.fetchTimeSeriesData(originalUeId);
            console.log('Time series data received:', timeSeriesData);
            console.log('Data length:', timeSeriesData.length);
            this.displayTimeSeriesModal(originalUeId, timeSeriesData);
        } catch (error) {
            console.error('Error fetching time series:', error);
            this.showError('Failed to load time series data');
        }
    }

    async fetchTimeSeriesData(ueId) {
        const timeRange = document.getElementById('timeRange').value;
        console.log('Fetching time series for UE:', ueId, 'with time range:', timeRange);
        
        const query = `
            from(bucket: "${this.config.influxdb.bucket}")
                |> range(start: ${this.getTimeRangeStart(timeRange)}, stop: now())
                |> filter(fn: (r) => r.ue_id == "${ueId}")
                |> sort(columns: ["_time"])
                |> limit(n: 100)
        `;

        console.log('Time series query:', query);

        const response = await fetch('/api/v2/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Time series response error:', response.status, errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.text();
        console.log('Time series raw response:', data);
        const parsedData = this.parseFluxResponse(data);
        console.log('Time series parsed data:', parsedData);
        return parsedData;
    }

    displayTimeSeriesModal(ueId, data) {
        const modal = document.getElementById('timeSeriesModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.querySelector('.modal-body');
        
        modalTitle.textContent = `UE ${ueId} Time Series Data`;
        
        console.log('Time series data for charts:', data);
        
        if (data.length === 0) {
            // Show message if no data
            modalBody.innerHTML = '<p>No time series data available for this UE.</p>';
            modal.classList.remove('hidden');
            return;
        }
        
        // Store the data for chart updates
        this.currentTimeSeriesData = data;
        
        // Group data by field
        const fieldGroups = {};
        data.forEach(record => {
            const field = record.field || 'unknown';
            if (!fieldGroups[field]) {
                fieldGroups[field] = [];
            }
            fieldGroups[field].push(record);
        });
        
        // Populate field dropdown (exclude non-numeric fields)
        const fieldSelect = document.getElementById('fieldSelect');
        fieldSelect.innerHTML = '';
        
        // Filter out string fields that aren't suitable for charting
        const chartableFields = Object.keys(fieldGroups).filter(field => {
            // Exclude known string fields that shouldn't be charted
            const excludedFields = ['ue_type', 'measurement', 'field'];
            if (excludedFields.includes(field)) {
                return false;
            }
            
            // Also check if the field contains numeric values by examining sample data
            const sampleRecord = fieldGroups[field][0];
            if (sampleRecord && sampleRecord.value !== undefined) {
                const numericValue = parseFloat(sampleRecord.value);
                return !isNaN(numericValue);
            }
            
            return true;
        });
        
        if (chartableFields.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No numeric fields available for charting';
            fieldSelect.appendChild(option);
        } else {
            chartableFields.forEach(field => {
                const option = document.createElement('option');
                option.value = field;
                option.textContent = field;
                fieldSelect.appendChild(option);
            });
        }
        
        // Set up field change event
        fieldSelect.onchange = () => {
            this.updateChart(fieldSelect.value);
        };
        
        // Show modal and create initial chart
        modal.classList.remove('hidden');
        if (chartableFields.length > 0) {
            this.updateChart(chartableFields[0]);
        }
    }

    updateChart(selectedField) {
        if (!this.currentTimeSeriesData) return;
        
        // Filter data for selected field
        const fieldData = this.currentTimeSeriesData.filter(record => record.field === selectedField);
        
        // Destroy existing chart
        if (this.timeSeriesChart) {
            this.timeSeriesChart.destroy();
        }
        
        const canvas = document.getElementById('timeSeriesChart');
        const ctx = canvas.getContext('2d');
        
        this.timeSeriesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: fieldData.map(d => new Date(d.timestamp).toLocaleString()),
                datasets: [{
                    label: selectedField,
                    data: fieldData.map(d => d.value),
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.1,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#3498db',
                    pointBorderColor: '#2980b9'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return 'Time: ' + context[0].label;
                            },
                            label: function(context) {
                                return selectedField + ': ' + context.parsed.y;
                            }
                        }
                    },
                    legend: {
                        display: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: selectedField
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    hideModal() {
        document.getElementById('timeSeriesModal').classList.add('hidden');
        if (this.timeSeriesChart) {
            this.timeSeriesChart.destroy();
            this.timeSeriesChart = null;
        }
        this.currentTimeSeriesData = null;
    }

    showError(message) {
        // Simple error display - you might want to enhance this
        alert(message);
    }

    setupAutoRefresh() {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadData();
        }, 30000);
    }

    async debugData() {
        try {
            console.log('Debugging InfluxDB data...');
            const response = await fetch('/api/debug');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.text();
            console.log('Debug data from InfluxDB:', data);
            
            // Show debug data in modal
            const modal = document.getElementById('timeSeriesModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.querySelector('.modal-body');
            
            modalTitle.textContent = 'Debug: InfluxDB Data';
            modalBody.innerHTML = `<pre style="white-space: pre-wrap; font-size: 12px;">${data}</pre>`;
            modal.classList.remove('hidden');
        } catch (error) {
            console.error('Error debugging data:', error);
            this.showError('Failed to debug data');
        }
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new TwinRANTopology();
}); 