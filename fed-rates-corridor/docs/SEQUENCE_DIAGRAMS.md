# Sequence Diagrams

## 1. Data Download Sequence (Public CSV Endpoint)

```mermaid
sequenceDiagram
    participant User
    participant Script as download_rates.py
    participant Env as Environment
    participant FRED as FRED CSV Endpoint
    participant FS as File System

    User->>Script: python download_rates.py
    Script->>Env: Check FRED_API_KEY
    Env-->>Script: Not set (empty)
    Script->>Script: Select public CSV method

    Note over Script: Iterate over 8 series

    loop For each series (DFEDTARU, DFEDTARL, IORB, SOFR, DFF, TGCRRATE, RRPONTSYAWARD, SRFTSYD)
        Script->>FRED: GET /graph/fredgraph.csv?id={series}&cosd=2000-01-01
        FRED-->>Script: CSV Response (observation_date, value)
        Script->>FS: Write data/{series}.csv
        FS-->>Script: File written ({size} bytes)
        Script->>User: Print progress
    end

    Script->>User: Done. 8/8 series downloaded.
```

## 2. Data Download Sequence (fredapi Library)

```mermaid
sequenceDiagram
    participant User
    participant Script as download_rates.py
    participant Env as Environment
    participant FredAPI as fredapi.Fred
    participant FRED as FRED REST API
    participant FS as File System

    User->>Script: FRED_API_KEY=xxx python download_rates.py
    Script->>Env: Check FRED_API_KEY
    Env-->>Script: API key found
    Script->>Script: Select fredapi method

    loop For each series
        Script->>FredAPI: Fred(api_key).get_series(series_id, start)
        FredAPI->>FRED: GET /fred/series/observations?series_id={id}&api_key={key}
        FRED-->>FredAPI: XML/JSON response with observations
        FredAPI-->>Script: pandas.Series (datetime-indexed)
        Script->>Script: Convert to DataFrame
        Script->>FS: Write data/{series}.csv
        Script->>User: Print progress
    end

    Script->>User: Done. 8/8 series downloaded.
```

## 3. Analysis & Chart Generation Sequence

```mermaid
sequenceDiagram
    participant User
    participant Script as analyze_rates.py
    participant FS as File System
    participant Loader as Data Loader
    participant Stats as Statistics Engine
    participant Chart as Chart Generator
    participant MPL as Matplotlib

    User->>Script: python analyze_rates.py
    Script->>Script: Apply Fed stylesheet (rcParams)

    Note over Script,Loader: Phase 1: Data Loading

    loop For each of 8 series
        Script->>Loader: load_series(series_id)
        Loader->>FS: Read data/{series_id}.csv
        FS-->>Loader: Raw CSV content
        Loader->>Loader: Parse dates, handle NaN, normalize columns
        Loader-->>Script: DataFrame (date-indexed, 'value' column)
    end

    Note over Script,Chart: Phase 2: Full Historical Chart

    Script->>Chart: plot_rate_corridor(data, path)
    Chart->>MPL: Create figure (14x7, 150 DPI)
    Chart->>MPL: Add recession shading (NBER dates)

    loop For each series in plot order
        Chart->>MPL: Plot line (color, style, width per series)
    end

    Chart->>MPL: Fill corridor between DFEDTARU and DFEDTARL
    Chart->>MPL: Add title, labels, legend, source footer
    Chart->>FS: savefig(fed_rates_corridor.png)

    Note over Script,Chart: Phase 3: 1-Year View Chart

    Script->>Chart: plot_recent_corridor(data, path)
    Chart->>Chart: Filter data to last 12 months
    Chart->>MPL: Create figure with same styling
    Chart->>MPL: Plot filtered series
    Chart->>FS: savefig(fed_rates_corridor_1yr.png)

    Note over Script,Stats: Phase 4: Summary Statistics

    Script->>Stats: compute_summary(data)
    Stats->>Stats: Calculate latest, min, max, mean per series
    Stats->>Stats: Calculate corridor width (bps)
    Stats-->>Script: Summary dict
    Script->>FS: Write output/rates_summary.json

    Script->>User: Print current rates table
```

## 4. MCP Integration Sequence (fred-mcp-server)

```mermaid
sequenceDiagram
    participant LLM as LLM Client<br/>(Claude, etc.)
    participant MCP as fred-mcp-server
    participant FRED as FRED REST API

    Note over LLM,FRED: Discovery Phase

    LLM->>MCP: initialize (MCP handshake)
    MCP-->>LLM: capabilities (tools: fred_browse, fred_search, fred_get_series)

    Note over LLM,FRED: Data Retrieval Phase

    LLM->>MCP: call_tool("fred_search", {query: "federal funds rate"})
    MCP->>FRED: GET /fred/series/search?search_text=federal+funds+rate
    FRED-->>MCP: Series list (DFF, DFEDTARU, DFEDTARL, ...)
    MCP-->>LLM: Formatted search results

    LLM->>MCP: call_tool("fred_get_series", {series_id: "DFF", limit: 30})
    MCP->>FRED: GET /fred/series/observations?series_id=DFF
    FRED-->>MCP: Observation data
    MCP->>MCP: Apply transformations (if requested)
    MCP-->>LLM: Formatted time series data

    Note over LLM,FRED: Analysis Phase

    LLM->>LLM: Analyze rate corridor data
    LLM-->>LLM: Generate insights and recommendations
```

## 5. End-to-End Pipeline Sequence

```mermaid
sequenceDiagram
    participant User as Economic Researcher
    participant DL as download_rates.py
    participant FRED as FRED Platform
    participant AZ as analyze_rates.py
    participant OUT as Output Files
    participant REV as Review/Presentation

    Note over User,REV: Complete Workflow

    User->>DL: Execute download script
    activate DL
    DL->>FRED: Fetch 8 rate series (CSV)
    FRED-->>DL: ~500KB total CSV data
    DL->>DL: Save to data/ directory
    deactivate DL

    User->>AZ: Execute analysis script
    activate AZ
    AZ->>AZ: Load & parse all CSVs
    AZ->>AZ: Generate full history chart
    AZ->>AZ: Generate 1-year chart
    AZ->>AZ: Compute summary statistics
    AZ->>OUT: Write PNGs + JSON
    deactivate AZ

    User->>OUT: Review generated artifacts
    OUT-->>User: Charts + Statistics

    User->>REV: Include in research report
    Note over REV: Ready for FOMC briefing<br/>or research publication
```

## 6. Error Handling Sequence

```mermaid
sequenceDiagram
    participant User
    participant Script as download_rates.py
    participant FRED as FRED Endpoint
    participant FS as File System

    User->>Script: python download_rates.py

    Note over Script,FRED: Successful download
    Script->>FRED: GET fredgraph.csv?id=DFEDTARU
    FRED-->>Script: 200 OK (CSV data)
    Script->>FS: Write DFEDTARU.csv ✓

    Note over Script,FRED: Network failure
    Script->>FRED: GET fredgraph.csv?id=SOFR
    FRED-->>Script: Connection timeout / HTTP 500
    Script->>Script: Catch exception
    Script->>User: ERROR (SOFR): Connection timeout
    Script->>Script: Add to errors list

    Note over Script: Continue with remaining series...

    Script->>FRED: GET fredgraph.csv?id=DFF
    FRED-->>Script: 200 OK (CSV data)
    Script->>FS: Write DFF.csv ✓

    Script->>User: Done. 7/8 series downloaded.
    Script->>User: Failed: SOFR (exit code 1)
```
