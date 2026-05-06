# Architecture Diagrams

## System Context (C4 Level 1)

```mermaid
graph TB
    subgraph "Users"
        ER[Economic Research Team]
        DS[Data Scientists]
    end

    subgraph "Fed Rates Corridor System"
        FRC[Fed Rates Corridor<br/>Analysis Pipeline]
    end

    subgraph "External Data Sources"
        FRED[FRED API<br/>Federal Reserve Economic Data<br/>St. Louis Fed]
        BOG[Board of Governors<br/>Federal Reserve System]
        NYFED[Federal Reserve Bank<br/>of New York]
    end

    subgraph "Integration Layer"
        FREDAPI[fredapi<br/>Python FRED Client]
        MCP[fred-mcp-server<br/>MCP Protocol Server]
    end

    ER -->|Views charts & reports| FRC
    DS -->|Runs analysis pipeline| FRC
    FRC -->|Fetches rate data| FRED
    FRED ---|Publishes data from| BOG
    FRED ---|Publishes data from| NYFED
    FREDAPI -->|API calls| FRED
    MCP -->|API calls| FRED
    FRC -.->|Optional: uses| FREDAPI
    DS -.->|LLM queries via| MCP
```

## Container Diagram (C4 Level 2)

```mermaid
graph LR
    subgraph "Fed Rates Corridor Pipeline"
        DL[Data Downloader<br/>download_rates.py]
        AE[Analysis Engine<br/>analyze_rates.py]
        DS[Data Store<br/>data/*.csv]
        OUT[Output Artifacts<br/>output/]
    end

    subgraph "External"
        FRED[(FRED Database<br/>800K+ Series)]
    end

    DL -->|HTTP GET CSV| FRED
    DL -->|Writes CSV files| DS
    AE -->|Reads CSV files| DS
    AE -->|Generates| OUT

    style FRED fill:#e1f5fe
    style DS fill:#fff3e0
    style OUT fill:#e8f5e9
```

## Component Diagram (C4 Level 3)

```mermaid
graph TB
    subgraph "download_rates.py"
        SERIES_CONFIG[Series Configuration<br/>8 FRED Series IDs]
        CSV_DL[CSV Downloader<br/>Public Endpoint]
        API_DL[fredapi Downloader<br/>Authenticated]
        ROUTE{API Key<br/>Available?}

        SERIES_CONFIG --> ROUTE
        ROUTE -->|No| CSV_DL
        ROUTE -->|Yes| API_DL
    end

    subgraph "analyze_rates.py"
        LOADER[Data Loader<br/>CSV Parser]
        STATS[Statistics Engine<br/>Summary Computations]
        STYLE[Fed Stylesheet<br/>RC Params]
        FULL_CHART[Full Historical<br/>Chart Generator]
        YR_CHART[1-Year View<br/>Chart Generator]
        RECESSION[Recession Shader<br/>NBER Dates]
    end

    subgraph "Output"
        PNG1[fed_rates_corridor.png]
        PNG2[fed_rates_corridor_1yr.png]
        JSON[rates_summary.json]
    end

    CSV_DL -->|CSV Files| LOADER
    API_DL -->|CSV Files| LOADER
    LOADER --> STATS
    LOADER --> FULL_CHART
    LOADER --> YR_CHART
    STYLE --> FULL_CHART
    STYLE --> YR_CHART
    RECESSION --> FULL_CHART
    STATS --> JSON
    FULL_CHART --> PNG1
    YR_CHART --> PNG2
```

## Deployment Diagram

```mermaid
graph TB
    subgraph "Developer Workstation"
        PY[Python 3.10+ Runtime]
        VENV[Virtual Environment]
        GIT[Git Repository]
    end

    subgraph "CI/CD Pipeline"
        GHA[GitHub Actions]
        LINT[Lint & Type Check<br/>black, isort, flake8]
        TEST[Test Runner<br/>pytest]
    end

    subgraph "Data Flow"
        FRED_API[FRED Public API<br/>fred.stlouisfed.org]
        CSV_EP[CSV Endpoint<br/>fredgraph.csv]
    end

    subgraph "Outputs"
        CHARTS[Chart PNGs<br/>150 DPI]
        STATS_JSON[Statistics JSON]
        DOCS[Documentation<br/>Markdown + Diagrams]
    end

    PY --> VENV
    VENV -->|pip install| GIT
    GIT -->|push| GHA
    GHA --> LINT
    GHA --> TEST
    PY -->|HTTP Request| CSV_EP
    CSV_EP -->|Response| PY
    FRED_API --> CSV_EP
    PY --> CHARTS
    PY --> STATS_JSON
    GIT --> DOCS
```

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph "Sources"
        S1[Board of Governors<br/>DFEDTARU, DFEDTARL,<br/>IORB, DFF]
        S2[NY Fed<br/>SOFR, TGCRRATE,<br/>RRPONTSYAWARD, SRFTSYD]
    end

    subgraph "FRED Platform"
        DB[(FRED Database)]
        API[REST API /<br/>CSV Endpoint]
    end

    subgraph "Pipeline"
        DL[Download Module]
        STORE[Local CSV Store<br/>data/]
        PARSE[CSV Parser /<br/>Data Loader]
        COMPUTE[Statistics<br/>Computation]
        VIZ[Visualization<br/>Engine]
    end

    subgraph "Outputs"
        C1[Full History Chart]
        C2[1-Year Chart]
        J[Summary JSON]
    end

    S1 -->|Publishes| DB
    S2 -->|Publishes| DB
    DB --> API
    API -->|CSV Response| DL
    DL -->|Write| STORE
    STORE -->|Read| PARSE
    PARSE --> COMPUTE
    PARSE --> VIZ
    COMPUTE --> J
    VIZ --> C1
    VIZ --> C2
```

## Rate Corridor Conceptual Model

```mermaid
graph TB
    subgraph "Federal Reserve Rate Corridor"
        direction TB
        SRP[Standing Repo Rate<br/>SRFTSYD — Ceiling Backstop<br/>Currently: 3.75%]
        UPPER[Target Range Upper Limit<br/>DFEDTARU<br/>Currently: 3.75%]
        IORB_R[IORB Rate<br/>Primary Steering Tool<br/>Currently: 3.65%]
        DFF_R[Fed Funds Effective Rate<br/>DFF<br/>Currently: 3.64%]
        SOFR_R[SOFR<br/>Treasury Repo Benchmark<br/>Currently: 3.62%]
        TGCR_R[Tri-Party GC Rate<br/>TGCRRATE<br/>Currently: 3.60%]
        RRP[ON RRP Award Rate<br/>RRPONTSYAWARD — Floor<br/>Currently: 3.50%]
        LOWER[Target Range Lower Limit<br/>DFEDTARL<br/>Currently: 3.50%]
    end

    SRP --- UPPER
    UPPER --- IORB_R
    IORB_R --- DFF_R
    DFF_R --- SOFR_R
    SOFR_R --- TGCR_R
    TGCR_R --- RRP
    RRP --- LOWER

    style SRP fill:#ffcdd2
    style UPPER fill:#1f4e79,color:#fff
    style IORB_R fill:#2e75b6,color:#fff
    style DFF_R fill:#7030a0,color:#fff
    style SOFR_R fill:#548235,color:#fff
    style TGCR_R fill:#ed7d31,color:#fff
    style RRP fill:#70ad47,color:#fff
    style LOWER fill:#1f4e79,color:#fff
```
