# Stock Market R Dashboard

Interactive R Shiny dashboard for time series analysis and forecasting of stocks driving the market since the pandemic, organized into four thematic categories:

| Category | Focus | Example Tickers |
|---|---|---|
| AI & Machine Learning | Companies leading AI innovation | NVDA, MSFT, GOOGL, META, AMD |
| Capital Expenditure (Capex) | Infrastructure and industrial companies | CAT, DE, URI, ETN, EMR |
| Data Storage & Cloud | Storage, cloud, and enterprise tech | STX, WDC, NTAP, PURE, NET |
| Pandemic Market Drivers | Mega-cap stocks shaping post-COVID trends | AAPL, TSLA, AMZN, NFLX, UNH |

## Features

- **Overview Dashboard** - Normalized price performance, summary metrics, and performance table
- **Time Series Analysis** - Individual stock charts with moving averages, returns, and descriptive statistics
- **Comparative Analysis** - Side-by-side cumulative returns and monthly returns heatmap
- **Volatility Analysis** - Rolling annualized volatility with S&P 500 benchmark overlay
- **Correlation Matrix** - Return correlations with adjustable time windows
- **Trend Forecasting** - ARIMA, ETS, and TBATS models with confidence intervals and diagnostics
- **Data Explorer** - Searchable OHLCV table with CSV export

## Prerequisites

- R >= 4.1
- System libraries: `libcurl4-openssl-dev`, `libssl-dev`, `libxml2-dev`, `libfontconfig1-dev`, `libharfbuzz-dev`, `libfribidi-dev`

## Setup

```bash
# Install R packages
Rscript -e 'install.packages(c(
  "shiny", "shinydashboard", "quantmod", "forecast",
  "plotly", "dplyr", "tidyr", "DT", "xts", "zoo",
  "tseries", "ggplot2", "shinycssloaders"
), repos = "https://cloud.r-project.org")'
```

## Run

```bash
Rscript -e "shiny::runApp('stock-market-dashboard', port = 3838, host = '0.0.0.0')"
```

Then open [http://localhost:3838](http://localhost:3838) in your browser.

## Tech Stack

- **R Shiny** + **shinydashboard** - UI framework
- **quantmod** - Yahoo Finance data retrieval
- **forecast** - ARIMA / ETS / TBATS time series models
- **plotly** - Interactive visualizations
- **DT** - Sortable, searchable data tables

## Data Source

All stock price data is fetched live from Yahoo Finance via the `quantmod` package. No API key is required.
