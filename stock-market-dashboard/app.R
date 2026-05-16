# ---------------------------------------------------------------------------
# Stock Market R Dashboard - Time Series Analysis & Forecasting
#
# Interactive Shiny dashboard for analyzing AI, Capex, Storage, and related
# stocks driving the market since the pandemic, with trend forecasting.
#
# Usage:
#   Rscript -e "shiny::runApp('stock-market-dashboard', port = 3838)"
# ---------------------------------------------------------------------------

library(shiny)
library(shinydashboard)
library(quantmod)
library(forecast)
library(plotly)
library(dplyr)
library(tidyr)
library(DT)
library(xts)
library(zoo)
library(tseries)
library(shinycssloaders)

source("ai_module.R", local = TRUE)

# ---------------------------------------------------------------------------
# Stock Universe - Categories
# ---------------------------------------------------------------------------
STOCK_CATEGORIES <- list(
  "AI & Machine Learning" = list(
    tickers = c("NVDA", "MSFT", "GOOGL", "META", "AMD", "AMZN", "CRM", "PLTR", "SNOW", "AVGO"),
    description = "Companies leading artificial intelligence innovation and deployment",
    color = "#2196F3"
  ),
  "Capital Expenditure (Capex)" = list(
    tickers = c("CAT", "DE", "URI", "ETN", "EMR", "VMC", "MLM", "PCAR", "ROK", "AME"),
    description = "Infrastructure and industrial companies benefiting from capex cycles",
    color = "#FF9800"
  ),
  "Data Storage & Cloud" = list(
    tickers = c("STX", "WDC", "NTAP", "PURE", "NET", "DDOG", "MDB", "DELL", "HPE", "IBM"),
    description = "Data storage, cloud infrastructure, and enterprise technology",
    color = "#4CAF50"
  ),
  "Pandemic Market Drivers" = list(
    tickers = c("AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "NFLX", "COST", "UNH"),
    description = "Mega-cap and growth stocks that shaped market trends since COVID-19",
    color = "#9C27B0"
  )
)

PANDEMIC_START <- as.Date("2020-01-01")

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
fetch_stock_data <- function(ticker, from_date = PANDEMIC_START) {
  tryCatch({
    data <- getSymbols(ticker, src = "yahoo", from = from_date, auto.assign = FALSE)
    if (is.null(data) || nrow(data) == 0) return(NULL)
    data
  }, error = function(e) {
    message(paste("Error fetching", ticker, ":", e$message))
    NULL
  })
}

compute_returns <- function(prices) {
  returns <- diff(log(prices))
  returns[is.infinite(returns)] <- NA
  na.omit(returns)
}

compute_rolling_volatility <- function(returns, window = 21) {
  rollapply(returns, width = window, FUN = sd, fill = NA, align = "right") * sqrt(252)
}

normalize_prices <- function(price_series) {
  first_val <- as.numeric(price_series[1])
  if (is.na(first_val) || first_val == 0) return(price_series)
  (price_series / first_val - 1) * 100
}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
ui <- dashboardPage(
  skin = "blue",
  dashboardHeader(
    title = span(
      icon("chart-line"),
      "Stock Market Dashboard"
    ),
    titleWidth = 320
  ),

  dashboardSidebar(
    width = 320,
    sidebarMenu(
      id = "tabs",
      menuItem("Overview", tabName = "overview", icon = icon("tachometer-alt")),
      menuItem("Time Series Analysis", tabName = "timeseries", icon = icon("chart-area")),
      menuItem("Comparative Analysis", tabName = "comparative", icon = icon("balance-scale")),
      menuItem("Volatility Analysis", tabName = "volatility", icon = icon("bolt")),
      menuItem("Correlation Matrix", tabName = "correlation", icon = icon("th")),
      menuItem("Forecasting", tabName = "forecast", icon = icon("chart-line")),
      menuItem("Data Explorer", tabName = "data", icon = icon("table")),
      hr(),
      menuItem("AI Insights", tabName = "ai_summary", icon = icon("brain")),
      menuItem("AI Chat", tabName = "ai_chat", icon = icon("comments"))
    ),
    hr(),
    selectInput(
      "category",
      "Stock Category:",
      choices = names(STOCK_CATEGORIES),
      selected = names(STOCK_CATEGORIES)[1]
    ),
    uiOutput("ticker_selector"),
    dateRangeInput(
      "date_range",
      "Date Range:",
      start = PANDEMIC_START,
      end = Sys.Date(),
      min = as.Date("2019-01-01"),
      max = Sys.Date()
    ),
    hr(),
    conditionalPanel(
      condition = "input.tabs == 'ai_summary' || input.tabs == 'ai_chat'",
      selectInput(
        "ai_provider", "AI Provider:",
        choices = c("OpenAI" = "openai", "AWS Bedrock" = "bedrock"),
        selected = AI_DEFAULTS$provider
      ),
      conditionalPanel(
        condition = "input.ai_provider == 'openai'",
        passwordInput("openai_key", "OpenAI API Key:",
                      value = AI_DEFAULTS$openai_key,
                      placeholder = "sk-..."),
        selectInput("openai_model", "Model:",
                    choices = c("gpt-4o" = "gpt-4o",
                                "gpt-4o-mini" = "gpt-4o-mini",
                                "gpt-4-turbo" = "gpt-4-turbo",
                                "gpt-3.5-turbo" = "gpt-3.5-turbo"),
                    selected = AI_DEFAULTS$openai_model)
      ),
      conditionalPanel(
        condition = "input.ai_provider == 'bedrock'",
        textInput("bedrock_region", "AWS Region:",
                  value = AI_DEFAULTS$bedrock_region),
        selectInput("bedrock_model", "Model:",
                    choices = c(
                      "Claude 3.5 Sonnet" = "anthropic.claude-3-5-sonnet-20241022-v2:0",
                      "Claude 3 Sonnet"   = "anthropic.claude-3-sonnet-20240229-v1:0",
                      "Claude 3 Haiku"    = "anthropic.claude-3-haiku-20240307-v1:0",
                      "Titan Text"        = "amazon.titan-text-express-v1"
                    ),
                    selected = AI_DEFAULTS$bedrock_model),
        div(style = "padding: 0 15px; font-size: 11px; color: #aaa;",
            p("Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from env."))
      )
    ),
    hr(),
    div(
      style = "padding: 10px; font-size: 11px; color: #888;",
      p("Data sourced from Yahoo Finance."),
      p("Time series analysis includes ARIMA/ETS forecasting models."),
      p(paste("Last updated:", Sys.Date()))
    )
  ),

  dashboardBody(
    tags$head(
      tags$script(HTML("
        Shiny.addCustomMessageHandler('bindEnterKey', function(msg) {
          var el = document.getElementById(msg.inputId);
          if (el && !el.dataset.enterBound) {
            el.dataset.enterBound = 'true';
            el.addEventListener('keypress', function(e) {
              if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById(msg.buttonId).click();
              }
            });
          }
        });
        // Auto-scroll chat container on mutation
        var chatObs = new MutationObserver(function() {
          var c = document.getElementById('chat-scroll-container');
          if (c) c.scrollTop = c.scrollHeight;
        });
        document.addEventListener('DOMContentLoaded', function() {
          var target = document.getElementById('chat-scroll-container');
          if (target) chatObs.observe(target, {childList: true, subtree: true});
        });
        // Re-observe after Shiny renders
        $(document).on('shiny:value', function() {
          setTimeout(function() {
            var c = document.getElementById('chat-scroll-container');
            if (c) {
              chatObs.disconnect();
              chatObs.observe(c, {childList: true, subtree: true});
              c.scrollTop = c.scrollHeight;
            }
          }, 100);
        });
      ")),
      tags$style(HTML("
        .content-wrapper { background-color: #f5f7fa; }
        .small-box { border-radius: 8px; }
        .box { border-radius: 8px; border-top: 3px solid #3c8dbc; }
        .box-header { padding: 12px 15px; }
        .info-box { border-radius: 8px; min-height: 80px; }
        .main-header .logo { font-weight: bold; }
        .skin-blue .main-header .navbar { background-color: #1a237e; }
        .skin-blue .main-header .logo { background-color: #0d1642; }
        .skin-blue .main-sidebar { background-color: #1c2833; }
        .category-badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 12px;
          color: white;
          font-size: 12px;
          font-weight: 600;
          margin-bottom: 10px;
        }
        .metric-highlight {
          font-size: 24px;
          font-weight: 700;
          color: #1a237e;
        }
        .forecast-note {
          background: #fff3e0;
          border-left: 4px solid #ff9800;
          padding: 10px 14px;
          margin: 10px 0;
          border-radius: 0 4px 4px 0;
          font-size: 13px;
        }
        .ai-summary-box {
          background: #ffffff;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 20px;
          margin: 10px 0;
          white-space: pre-wrap;
          font-size: 14px;
          line-height: 1.6;
        }
        .chat-container {
          height: 500px;
          overflow-y: auto;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 15px;
          background: #fafafa;
          margin-bottom: 10px;
        }
        .chat-msg {
          margin-bottom: 12px;
          padding: 10px 14px;
          border-radius: 12px;
          max-width: 85%;
          line-height: 1.5;
          font-size: 14px;
          white-space: pre-wrap;
        }
        .chat-msg-user {
          background: #1a237e;
          color: white;
          margin-left: auto;
          text-align: right;
          border-bottom-right-radius: 4px;
        }
        .chat-msg-ai {
          background: #ffffff;
          color: #333;
          border: 1px solid #e0e0e0;
          border-bottom-left-radius: 4px;
        }
        .chat-msg-label {
          font-size: 11px;
          font-weight: 600;
          margin-bottom: 4px;
          opacity: 0.7;
        }
        .chat-input-row {
          display: flex;
          gap: 8px;
          align-items: flex-start;
        }
        .chat-input-row .form-group {
          flex: 1;
          margin-bottom: 0;
        }
      "))
    ),

    tabItems(
      # ---- Overview Tab ----
      tabItem(
        tabName = "overview",
        fluidRow(
          column(12,
            h2("Market Dashboard: Post-Pandemic Stock Trends"),
            uiOutput("category_description")
          )
        ),
        fluidRow(
          valueBoxOutput("total_return_box", width = 3),
          valueBoxOutput("best_performer_box", width = 3),
          valueBoxOutput("worst_performer_box", width = 3),
          valueBoxOutput("avg_volatility_box", width = 3)
        ),
        fluidRow(
          box(
            title = "Normalized Price Performance (% Change from Start)",
            width = 12, status = "primary", solidHeader = TRUE,
            withSpinner(plotlyOutput("overview_chart", height = "500px"))
          )
        ),
        fluidRow(
          box(
            title = "Performance Summary Table",
            width = 12, status = "info", solidHeader = TRUE,
            withSpinner(DT::dataTableOutput("summary_table"))
          )
        )
      ),

      # ---- Time Series Analysis Tab ----
      tabItem(
        tabName = "timeseries",
        fluidRow(
          column(12, h2("Individual Stock Time Series Analysis"))
        ),
        fluidRow(
          column(4,
            selectInput("ts_ticker", "Select Stock:", choices = NULL),
            radioButtons(
              "ts_metric", "Metric:",
              choices = c(
                "Closing Price" = "close",
                "Volume" = "volume",
                "Daily Returns" = "returns",
                "Cumulative Returns" = "cum_returns"
              ),
              selected = "close"
            ),
            checkboxInput("ts_show_ma", "Show Moving Averages", value = TRUE),
            conditionalPanel(
              condition = "input.ts_show_ma == true",
              sliderInput("ts_ma_short", "Short MA Window:", 10, 50, 20),
              sliderInput("ts_ma_long", "Long MA Window:", 50, 200, 50)
            )
          ),
          column(8,
            box(
              title = "Time Series Chart", width = NULL,
              status = "primary", solidHeader = TRUE,
              withSpinner(plotlyOutput("ts_chart", height = "450px"))
            )
          )
        ),
        fluidRow(
          box(
            title = "Descriptive Statistics", width = 6,
            status = "info", solidHeader = TRUE,
            withSpinner(DT::dataTableOutput("ts_stats"))
          ),
          box(
            title = "Distribution of Daily Returns", width = 6,
            status = "info", solidHeader = TRUE,
            withSpinner(plotlyOutput("ts_histogram", height = "300px"))
          )
        )
      ),

      # ---- Comparative Analysis Tab ----
      tabItem(
        tabName = "comparative",
        fluidRow(
          column(12, h2("Cross-Stock Comparative Analysis"))
        ),
        fluidRow(
          box(
            title = "Cumulative Returns Comparison", width = 12,
            status = "primary", solidHeader = TRUE,
            withSpinner(plotlyOutput("comp_returns", height = "500px"))
          )
        ),
        fluidRow(
          box(
            title = "Monthly Returns Heatmap", width = 12,
            status = "info", solidHeader = TRUE,
            withSpinner(plotlyOutput("comp_heatmap", height = "400px"))
          )
        )
      ),

      # ---- Volatility Tab ----
      tabItem(
        tabName = "volatility",
        fluidRow(
          column(12, h2("Volatility Analysis"))
        ),
        fluidRow(
          column(4,
            sliderInput("vol_window", "Rolling Window (trading days):", 10, 63, 21),
            checkboxInput("vol_compare_spy", "Overlay S&P 500 Volatility", value = TRUE)
          ),
          column(8,
            box(
              title = "Rolling Annualized Volatility", width = NULL,
              status = "warning", solidHeader = TRUE,
              withSpinner(plotlyOutput("vol_chart", height = "450px"))
            )
          )
        ),
        fluidRow(
          box(
            title = "Current Volatility Rankings", width = 12,
            status = "info", solidHeader = TRUE,
            withSpinner(plotlyOutput("vol_bar_chart", height = "350px"))
          )
        )
      ),

      # ---- Correlation Tab ----
      tabItem(
        tabName = "correlation",
        fluidRow(
          column(12, h2("Return Correlations"))
        ),
        fluidRow(
          column(4,
            selectInput(
              "corr_period", "Correlation Period:",
              choices = c(
                "Full Period" = "full",
                "Last 3 Months" = "3m",
                "Last 6 Months" = "6m",
                "Last 12 Months" = "12m"
              ),
              selected = "full"
            )
          ),
          column(8,
            box(
              title = "Correlation Matrix (Daily Returns)", width = NULL,
              status = "primary", solidHeader = TRUE,
              withSpinner(plotlyOutput("corr_matrix", height = "550px"))
            )
          )
        )
      ),

      # ---- Forecast Tab ----
      tabItem(
        tabName = "forecast",
        fluidRow(
          column(12, h2("Trend Forecasting"))
        ),
        fluidRow(
          column(4,
            selectInput("fc_ticker", "Stock to Forecast:", choices = NULL),
            selectInput(
              "fc_model", "Forecasting Model:",
              choices = c(
                "Auto ARIMA" = "arima",
                "ETS (Exponential Smoothing)" = "ets",
                "TBATS" = "tbats"
              ),
              selected = "arima"
            ),
            sliderInput("fc_horizon", "Forecast Horizon (trading days):", 5, 120, 30),
            sliderInput("fc_confidence", "Confidence Level (%):", 80, 99, 95),
            actionButton("fc_run", "Run Forecast", icon = icon("play"),
                         class = "btn-primary btn-block"),
            hr(),
            div(class = "forecast-note",
              icon("info-circle"),
              "Forecasts are statistical projections based on historical patterns. ",
              "They are not investment advice and carry significant uncertainty."
            )
          ),
          column(8,
            box(
              title = "Forecast Results", width = NULL,
              status = "success", solidHeader = TRUE,
              withSpinner(plotlyOutput("fc_chart", height = "450px"))
            ),
            box(
              title = "Model Diagnostics", width = NULL,
              status = "info", solidHeader = TRUE,
              verbatimTextOutput("fc_model_summary"),
              withSpinner(plotlyOutput("fc_residuals", height = "250px"))
            )
          )
        )
      ),

      # ---- Data Explorer Tab ----
      tabItem(
        tabName = "data",
        fluidRow(
          column(12, h2("Raw Data Explorer"))
        ),
        fluidRow(
          column(4,
            selectInput("data_ticker", "Select Stock:", choices = NULL),
            downloadButton("download_csv", "Download CSV", class = "btn-info btn-block")
          ),
          column(8,
            box(
              title = "OHLCV Data", width = NULL,
              status = "primary", solidHeader = TRUE,
              withSpinner(DT::dataTableOutput("data_table"))
            )
          )
        )
      ),

      # ---- AI Insights Tab ----
      tabItem(
        tabName = "ai_summary",
        fluidRow(
          column(12, h2("AI-Powered Dashboard Insights"))
        ),
        fluidRow(
          column(12,
            div(class = "forecast-note",
              icon("info-circle"),
              "Configure your AI provider in the sidebar. OpenAI requires an API key; ",
              "AWS Bedrock uses credentials from environment variables."
            )
          )
        ),
        fluidRow(
          column(4,
            box(
              title = "Generate Summary", width = NULL,
              status = "primary", solidHeader = TRUE,
              p("Analyze the current stock category with AI to generate
                an executive summary of performance, risk, and trends."),
              actionButton("ai_summarize", "Summarize Dashboard",
                           icon = icon("magic"),
                           class = "btn-primary btn-block",
                           style = "margin-top: 10px;"),
              hr(),
              radioButtons(
                "ai_summary_focus", "Summary Focus:",
                choices = c(
                  "Full Overview"         = "overview",
                  "Performance Analysis"  = "performance",
                  "Risk & Volatility"     = "risk",
                  "Trend & Momentum"      = "trend"
                ),
                selected = "overview"
              )
            )
          ),
          column(8,
            box(
              title = "AI Analysis", width = NULL,
              status = "success", solidHeader = TRUE,
              withSpinner(uiOutput("ai_summary_output"))
            )
          )
        )
      ),

      # ---- AI Chat Tab ----
      tabItem(
        tabName = "ai_chat",
        fluidRow(
          column(12, h2("Chat with Your Data"))
        ),
        fluidRow(
          column(12,
            box(
              title = "AI Assistant", width = 12,
              status = "primary", solidHeader = TRUE,
              uiOutput("chat_history_ui"),
              div(class = "chat-input-row",
                textInput("chat_input", label = NULL,
                          placeholder = "Ask a question about your stock data...",
                          width = "100%"),
                actionButton("chat_send", "", icon = icon("paper-plane"),
                             class = "btn-primary",
                             style = "height: 38px; margin-top: 0;")
              ),
              div(style = "margin-top: 8px;",
                actionButton("chat_clear", "Clear Chat",
                             icon = icon("trash"), class = "btn-default btn-sm"),
                span(style = "margin-left: 12px; font-size: 12px; color: #888;",
                     "Press Enter or click send. Context includes current category data.")
              )
            )
          )
        ),
        fluidRow(
          column(12,
            box(
              title = "Suggested Questions", width = 12,
              status = "info", solidHeader = TRUE, collapsible = TRUE, collapsed = TRUE,
              fluidRow(
                column(6,
                  actionButton("sq1", "Which stock has the best risk-adjusted return?",
                               class = "btn-default btn-block",
                               style = "text-align:left; margin-bottom:5px;"),
                  actionButton("sq2", "Compare the volatility of the top 3 performers",
                               class = "btn-default btn-block",
                               style = "text-align:left; margin-bottom:5px;"),
                  actionButton("sq3", "What trends do you see in the recent 3 months?",
                               class = "btn-default btn-block",
                               style = "text-align:left; margin-bottom:5px;")
                ),
                column(6,
                  actionButton("sq4", "Which stocks are most correlated?",
                               class = "btn-default btn-block",
                               style = "text-align:left; margin-bottom:5px;"),
                  actionButton("sq5", "Summarize the overall sector performance",
                               class = "btn-default btn-block",
                               style = "text-align:left; margin-bottom:5px;"),
                  actionButton("sq6", "What are the key risks in this category?",
                               class = "btn-default btn-block",
                               style = "text-align:left; margin-bottom:5px;")
                )
              )
            )
          )
        )
      )
    )
  )
)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
server <- function(input, output, session) {

  # ---- Reactive: Fetch stock data for selected category ----
  stock_data <- reactiveVal(list())
  spy_data <- reactiveVal(NULL)

  observe({
    cat_info <- STOCK_CATEGORIES[[input$category]]
    tickers <- cat_info$tickers
    from_date <- input$date_range[1]

    withProgress(message = "Fetching stock data...", value = 0, {
      result <- list()
      for (i in seq_along(tickers)) {
        incProgress(1 / length(tickers), detail = tickers[i])
        d <- fetch_stock_data(tickers[i], from_date)
        if (!is.null(d)) {
          result[[tickers[i]]] <- d
        }
      }
      stock_data(result)
    })

    spy <- fetch_stock_data("SPY", from_date)
    spy_data(spy)
  })

  # ---- Update ticker selectors ----
  observe({
    tickers <- names(stock_data())
    updateSelectInput(session, "ts_ticker", choices = tickers, selected = tickers[1])
    updateSelectInput(session, "fc_ticker", choices = tickers, selected = tickers[1])
    updateSelectInput(session, "data_ticker", choices = tickers, selected = tickers[1])
  })

  # ---- Reactive: selected tickers ----
  observe({
    cat_info <- STOCK_CATEGORIES[[input$category]]
    tickers <- cat_info$tickers
    updateCheckboxGroupInput(session, "ticker_select",
                             choices = tickers,
                             selected = tickers)
  })

  output$ticker_selector <- renderUI({
    cat_info <- STOCK_CATEGORIES[[input$category]]
    checkboxGroupInput(
      "ticker_select",
      "Select Stocks:",
      choices = cat_info$tickers,
      selected = cat_info$tickers
    )
  })

  selected_data <- reactive({
    all_data <- stock_data()
    sel <- input$ticker_select
    if (is.null(sel)) return(list())
    all_data[names(all_data) %in% sel]
  })

  # ---- Category description ----
  output$category_description <- renderUI({
    cat_info <- STOCK_CATEGORIES[[input$category]]
    div(
      span(class = "category-badge", style = paste0("background:", cat_info$color),
           input$category),
      p(cat_info$description, style = "color: #555; margin-top: 5px;")
    )
  })

  # ===========================================================================
  # OVERVIEW TAB
  # ===========================================================================
  overview_metrics <- reactive({
    data_list <- selected_data()
    if (length(data_list) == 0) return(NULL)

    metrics <- lapply(names(data_list), function(ticker) {
      d <- data_list[[ticker]]
      close_col <- paste0(ticker, ".Close")
      if (!(close_col %in% colnames(d))) return(NULL)
      prices <- Cl(d)
      first_price <- as.numeric(prices[1])
      last_price <- as.numeric(tail(prices, 1))
      total_return <- (last_price / first_price - 1) * 100
      log_ret <- compute_returns(prices)
      ann_vol <- sd(log_ret, na.rm = TRUE) * sqrt(252) * 100

      data.frame(
        Ticker = ticker,
        StartPrice = round(first_price, 2),
        EndPrice = round(last_price, 2),
        TotalReturn = round(total_return, 1),
        AnnVolatility = round(ann_vol, 1),
        stringsAsFactors = FALSE
      )
    })
    do.call(rbind, metrics)
  })

  output$total_return_box <- renderValueBox({
    m <- overview_metrics()
    avg_ret <- if (!is.null(m)) round(mean(m$TotalReturn, na.rm = TRUE), 1) else 0
    color <- if (avg_ret >= 0) "green" else "red"
    valueBox(paste0(avg_ret, "%"), "Avg Total Return",
             icon = icon("percent"), color = color)
  })

  output$best_performer_box <- renderValueBox({
    m <- overview_metrics()
    if (!is.null(m) && nrow(m) > 0) {
      best <- m[which.max(m$TotalReturn), ]
      valueBox(paste0(best$Ticker, ": ", ifelse(best$TotalReturn >= 0, "+", ""), best$TotalReturn, "%"), "Best Performer",
               icon = icon("arrow-up"), color = "green")
    } else {
      valueBox("N/A", "Best Performer", icon = icon("arrow-up"), color = "yellow")
    }
  })

  output$worst_performer_box <- renderValueBox({
    m <- overview_metrics()
    if (!is.null(m) && nrow(m) > 0) {
      worst <- m[which.min(m$TotalReturn), ]
      val <- paste0(worst$Ticker, ": ", worst$TotalReturn, "%")
      valueBox(val, "Worst Performer",
               icon = icon("arrow-down"), color = "red")
    } else {
      valueBox("N/A", "Worst Performer", icon = icon("arrow-down"), color = "yellow")
    }
  })

  output$avg_volatility_box <- renderValueBox({
    m <- overview_metrics()
    avg_vol <- if (!is.null(m)) round(mean(m$AnnVolatility, na.rm = TRUE), 1) else 0
    valueBox(paste0(avg_vol, "%"), "Avg Annualized Vol",
             icon = icon("bolt"), color = "purple")
  })

  output$overview_chart <- renderPlotly({
    data_list <- selected_data()
    if (length(data_list) == 0) return(plotly_empty())

    p <- plot_ly()
    colors <- rainbow(length(data_list))
    for (i in seq_along(data_list)) {
      ticker <- names(data_list)[i]
      d <- data_list[[ticker]]
      prices <- Cl(d)
      norm <- normalize_prices(prices)
      dates <- index(norm)
      vals <- as.numeric(norm)
      p <- p %>% add_trace(
        x = dates, y = vals, type = "scatter", mode = "lines",
        name = ticker, line = list(width = 2, color = colors[i])
      )
    }
    p %>% layout(
      title = list(text = "Normalized Price Performance Since Start Date", font = list(size = 16)),
      xaxis = list(title = "Date", rangeslider = list(visible = TRUE)),
      yaxis = list(title = "% Change from Start"),
      hovermode = "x unified",
      legend = list(orientation = "h", y = -0.25)
    )
  })

  output$summary_table <- DT::renderDataTable({
    m <- overview_metrics()
    if (is.null(m)) return(DT::datatable(data.frame()))
    colnames(m) <- c("Ticker", "Start Price ($)", "Current Price ($)",
                      "Total Return (%)", "Ann. Volatility (%)")
    DT::datatable(m, rownames = FALSE, options = list(pageLength = 15, dom = "t"),
                  class = "compact hover") %>%
      DT::formatStyle("Total Return (%)",
        color = DT::styleInterval(0, c("red", "green")),
        fontWeight = "bold"
      )
  })

  # ===========================================================================
  # TIME SERIES ANALYSIS TAB
  # ===========================================================================
  output$ts_chart <- renderPlotly({
    req(input$ts_ticker)
    data_list <- stock_data()
    req(input$ts_ticker %in% names(data_list))
    d <- data_list[[input$ts_ticker]]

    p <- plot_ly()

    if (input$ts_metric == "close") {
      prices <- Cl(d)
      p <- p %>% add_trace(
        x = index(prices), y = as.numeric(prices),
        type = "scatter", mode = "lines",
        name = "Close Price", line = list(color = "#1a237e", width = 1.5)
      )
      if (input$ts_show_ma) {
        ma_short <- SMA(prices, n = input$ts_ma_short)
        ma_long <- SMA(prices, n = input$ts_ma_long)
        p <- p %>%
          add_trace(x = index(ma_short), y = as.numeric(ma_short),
                    type = "scatter", mode = "lines",
                    name = paste0("MA-", input$ts_ma_short),
                    line = list(color = "#ff9800", width = 1.5, dash = "dash")) %>%
          add_trace(x = index(ma_long), y = as.numeric(ma_long),
                    type = "scatter", mode = "lines",
                    name = paste0("MA-", input$ts_ma_long),
                    line = list(color = "#e91e63", width = 1.5, dash = "dot"))
      }
      p <- p %>% layout(yaxis = list(title = "Price ($)"))

    } else if (input$ts_metric == "volume") {
      vol <- Vo(d)
      p <- p %>% add_trace(
        x = index(vol), y = as.numeric(vol),
        type = "bar", name = "Volume",
        marker = list(color = "#42a5f5", opacity = 0.7)
      ) %>% layout(yaxis = list(title = "Volume"))

    } else if (input$ts_metric == "returns") {
      prices <- Cl(d)
      ret <- compute_returns(prices)
      colors <- ifelse(as.numeric(ret) >= 0, "#4caf50", "#f44336")
      p <- p %>% add_trace(
        x = index(ret), y = as.numeric(ret) * 100,
        type = "bar", name = "Daily Return",
        marker = list(color = colors, opacity = 0.7)
      ) %>% layout(yaxis = list(title = "Daily Return (%)"))

    } else if (input$ts_metric == "cum_returns") {
      prices <- Cl(d)
      ret <- compute_returns(prices)
      cum_ret <- cumsum(ret) * 100
      p <- p %>% add_trace(
        x = index(cum_ret), y = as.numeric(cum_ret),
        type = "scatter", mode = "lines",
        name = "Cumulative Return",
        line = list(color = "#1a237e", width = 2),
        fill = "tozeroy", fillcolor = "rgba(26,35,126,0.1)"
      ) %>% layout(yaxis = list(title = "Cumulative Return (%)"))
    }

    p %>% layout(
      title = list(text = paste(input$ts_ticker, "-", input$ts_metric), font = list(size = 15)),
      xaxis = list(title = "Date", rangeslider = list(visible = TRUE)),
      hovermode = "x unified"
    )
  })

  output$ts_stats <- DT::renderDataTable({
    req(input$ts_ticker)
    data_list <- stock_data()
    req(input$ts_ticker %in% names(data_list))
    d <- data_list[[input$ts_ticker]]
    prices <- Cl(d)
    ret <- compute_returns(prices)
    ret_vals <- as.numeric(ret)

    stats <- data.frame(
      Statistic = c("Observations", "Mean Daily Return", "Std Dev (Daily)",
                     "Ann. Return", "Ann. Volatility", "Sharpe Ratio (rf=0)",
                     "Min Daily Return", "Max Daily Return", "Skewness", "Kurtosis"),
      Value = c(
        length(ret_vals),
        paste0(round(mean(ret_vals, na.rm = TRUE) * 100, 4), "%"),
        paste0(round(sd(ret_vals, na.rm = TRUE) * 100, 4), "%"),
        paste0(round(mean(ret_vals, na.rm = TRUE) * 252 * 100, 2), "%"),
        paste0(round(sd(ret_vals, na.rm = TRUE) * sqrt(252) * 100, 2), "%"),
        round(mean(ret_vals, na.rm = TRUE) / sd(ret_vals, na.rm = TRUE) * sqrt(252), 2),
        paste0(round(min(ret_vals, na.rm = TRUE) * 100, 2), "%"),
        paste0(round(max(ret_vals, na.rm = TRUE) * 100, 2), "%"),
        round(moments_skewness(ret_vals), 3),
        round(moments_kurtosis(ret_vals), 3)
      ),
      stringsAsFactors = FALSE
    )
    DT::datatable(stats, rownames = FALSE, options = list(dom = "t", pageLength = 15),
                  class = "compact")
  })

  output$ts_histogram <- renderPlotly({
    req(input$ts_ticker)
    data_list <- stock_data()
    req(input$ts_ticker %in% names(data_list))
    d <- data_list[[input$ts_ticker]]
    prices <- Cl(d)
    ret <- compute_returns(prices)
    ret_vals <- as.numeric(ret) * 100

    plot_ly(x = ret_vals, type = "histogram", nbinsx = 80,
            marker = list(color = "#42a5f5", line = list(color = "#1a237e", width = 0.5)),
            name = "Daily Returns") %>%
      layout(
        title = list(text = paste(input$ts_ticker, "- Return Distribution"), font = list(size = 14)),
        xaxis = list(title = "Daily Return (%)"),
        yaxis = list(title = "Frequency"),
        bargap = 0.05
      )
  })

  # ===========================================================================
  # COMPARATIVE ANALYSIS TAB
  # ===========================================================================
  output$comp_returns <- renderPlotly({
    data_list <- selected_data()
    if (length(data_list) == 0) return(plotly_empty())

    p <- plot_ly()
    colors <- rainbow(length(data_list))
    for (i in seq_along(data_list)) {
      ticker <- names(data_list)[i]
      d <- data_list[[ticker]]
      prices <- Cl(d)
      ret <- compute_returns(prices)
      cum_ret <- cumsum(ret) * 100
      p <- p %>% add_trace(
        x = index(cum_ret), y = as.numeric(cum_ret),
        type = "scatter", mode = "lines",
        name = ticker, line = list(width = 2, color = colors[i])
      )
    }
    p %>% layout(
      title = list(text = "Cumulative Returns Comparison", font = list(size = 16)),
      xaxis = list(title = "Date"),
      yaxis = list(title = "Cumulative Return (%)"),
      hovermode = "x unified",
      legend = list(orientation = "h", y = -0.15)
    )
  })

  output$comp_heatmap <- renderPlotly({
    data_list <- selected_data()
    if (length(data_list) < 2) return(plotly_empty())

    monthly_returns <- lapply(names(data_list), function(ticker) {
      d <- data_list[[ticker]]
      prices <- Cl(d)
      monthly <- to.monthly(prices, OHLC = FALSE)
      ret <- diff(log(monthly))
      ret <- na.omit(ret)
      data.frame(
        Date = format(index(ret), "%Y-%m"),
        Ticker = ticker,
        Return = round(as.numeric(ret) * 100, 2),
        stringsAsFactors = FALSE
      )
    })
    df <- do.call(rbind, monthly_returns)

    wide <- df %>% pivot_wider(names_from = Ticker, values_from = Return)
    mat <- as.matrix(wide[, -1])
    rownames(mat) <- wide$Date

    plot_ly(
      x = colnames(mat), y = rownames(mat), z = mat,
      type = "heatmap",
      colorscale = list(c(0, "#d32f2f"), c(0.5, "#ffffff"), c(1, "#388e3c")),
      zmid = 0,
      hovertemplate = "Stock: %{x}<br>Month: %{y}<br>Return: %{z}%<extra></extra>"
    ) %>% layout(
      title = list(text = "Monthly Returns Heatmap (%)", font = list(size = 15)),
      xaxis = list(title = ""),
      yaxis = list(title = "", autorange = "reversed")
    )
  })

  # ===========================================================================
  # VOLATILITY TAB
  # ===========================================================================
  output$vol_chart <- renderPlotly({
    data_list <- selected_data()
    if (length(data_list) == 0) return(plotly_empty())

    p <- plot_ly()
    colors <- rainbow(length(data_list))
    for (i in seq_along(data_list)) {
      ticker <- names(data_list)[i]
      d <- data_list[[ticker]]
      prices <- Cl(d)
      ret <- compute_returns(prices)
      vol <- compute_rolling_volatility(ret, window = input$vol_window)
      vol <- na.omit(vol)
      p <- p %>% add_trace(
        x = index(vol), y = as.numeric(vol) * 100,
        type = "scatter", mode = "lines",
        name = ticker, line = list(width = 1.5, color = colors[i])
      )
    }

    if (input$vol_compare_spy && !is.null(spy_data())) {
      spy_prices <- Cl(spy_data())
      spy_ret <- compute_returns(spy_prices)
      spy_vol <- compute_rolling_volatility(spy_ret, window = input$vol_window)
      spy_vol <- na.omit(spy_vol)
      p <- p %>% add_trace(
        x = index(spy_vol), y = as.numeric(spy_vol) * 100,
        type = "scatter", mode = "lines",
        name = "S&P 500 (SPY)", line = list(width = 2.5, color = "#000000", dash = "dash")
      )
    }

    p %>% layout(
      title = list(
        text = paste0("Rolling ", input$vol_window, "-Day Annualized Volatility"),
        font = list(size = 15)
      ),
      xaxis = list(title = "Date"),
      yaxis = list(title = "Annualized Volatility (%)"),
      hovermode = "x unified",
      legend = list(orientation = "h", y = -0.15)
    )
  })

  output$vol_bar_chart <- renderPlotly({
    data_list <- selected_data()
    if (length(data_list) == 0) return(plotly_empty())

    vol_data <- lapply(names(data_list), function(ticker) {
      d <- data_list[[ticker]]
      prices <- Cl(d)
      ret <- compute_returns(prices)
      recent_ret <- tail(ret, input$vol_window)
      ann_vol <- sd(recent_ret, na.rm = TRUE) * sqrt(252) * 100
      data.frame(Ticker = ticker, Volatility = round(ann_vol, 1), stringsAsFactors = FALSE)
    })
    df <- do.call(rbind, vol_data)
    df <- df[order(df$Volatility, decreasing = TRUE), ]

    plot_ly(
      x = reorder(df$Ticker, df$Volatility),
      y = df$Volatility,
      type = "bar",
      marker = list(
        color = df$Volatility,
        colorscale = list(c(0, "#4caf50"), c(0.5, "#ff9800"), c(1, "#f44336")),
        showscale = TRUE,
        colorbar = list(title = "Vol %")
      ),
      text = paste0(df$Volatility, "%"),
      textposition = "outside",
      hovertemplate = "%{x}: %{y:.1f}%<extra></extra>"
    ) %>% layout(
      title = list(text = "Current Volatility Rankings", font = list(size = 15)),
      xaxis = list(title = "", categoryorder = "total ascending"),
      yaxis = list(title = "Annualized Volatility (%)")
    )
  })

  # ===========================================================================
  # CORRELATION TAB
  # ===========================================================================
  output$corr_matrix <- renderPlotly({
    data_list <- selected_data()
    if (length(data_list) < 2) return(plotly_empty())

    returns_list <- lapply(names(data_list), function(ticker) {
      d <- data_list[[ticker]]
      prices <- Cl(d)
      ret <- compute_returns(prices)
      df <- data.frame(Date = index(ret), Return = as.numeric(ret), stringsAsFactors = FALSE)
      colnames(df)[2] <- ticker
      df
    })

    merged <- returns_list[[1]]
    for (i in 2:length(returns_list)) {
      merged <- merge(merged, returns_list[[i]], by = "Date", all = FALSE)
    }

    if (input$corr_period == "3m") {
      cutoff <- Sys.Date() - 90
      merged <- merged[merged$Date >= cutoff, ]
    } else if (input$corr_period == "6m") {
      cutoff <- Sys.Date() - 180
      merged <- merged[merged$Date >= cutoff, ]
    } else if (input$corr_period == "12m") {
      cutoff <- Sys.Date() - 365
      merged <- merged[merged$Date >= cutoff, ]
    }

    mat <- cor(merged[, -1], use = "pairwise.complete.obs")
    mat <- round(mat, 2)

    plot_ly(
      x = colnames(mat), y = rownames(mat), z = mat,
      type = "heatmap",
      colorscale = list(c(0, "#1565c0"), c(0.5, "#ffffff"), c(1, "#c62828")),
      zmin = -1, zmax = 1,
      text = mat, texttemplate = "%{text}",
      hovertemplate = "%{x} vs %{y}: %{z:.2f}<extra></extra>"
    ) %>% layout(
      title = list(text = "Return Correlation Matrix", font = list(size = 15)),
      xaxis = list(title = ""),
      yaxis = list(title = "", autorange = "reversed")
    )
  })

  # ===========================================================================
  # FORECASTING TAB
  # ===========================================================================
  forecast_result <- eventReactive(input$fc_run, {
    req(input$fc_ticker)
    data_list <- stock_data()
    req(input$fc_ticker %in% names(data_list))

    d <- data_list[[input$fc_ticker]]
    prices <- Cl(d)

    ts_data <- ts(as.numeric(prices), frequency = 252)

    model <- tryCatch({
      if (input$fc_model == "arima") {
        auto.arima(ts_data, stepwise = TRUE, approximation = TRUE)
      } else if (input$fc_model == "ets") {
        ets(ts_data)
      } else {
        tbats(ts_data)
      }
    }, error = function(e) {
      showNotification(paste("Model fitting error:", e$message), type = "error")
      NULL
    })

    if (is.null(model)) return(NULL)

    fc <- forecast(model, h = input$fc_horizon, level = input$fc_confidence)

    list(
      model = model,
      forecast = fc,
      prices = prices,
      ticker = input$fc_ticker,
      model_type = input$fc_model
    )
  })

  output$fc_chart <- renderPlotly({
    res <- forecast_result()
    if (is.null(res)) return(plotly_empty())

    prices <- res$prices
    fc <- res$forecast

    n_hist <- min(252, length(prices))
    hist_prices <- tail(prices, n_hist)
    hist_dates <- tail(index(prices), n_hist)

    last_date <- tail(index(prices), 1)
    fc_dates <- seq(last_date + 1, by = "day", length.out = ceiling(length(fc$mean) * 9 / 5) + 7)
    fc_dates <- fc_dates[!format(fc_dates, "%u") %in% c("6", "7")]
    fc_dates <- fc_dates[1:length(fc$mean)]

    p <- plot_ly() %>%
      add_trace(
        x = hist_dates, y = as.numeric(hist_prices),
        type = "scatter", mode = "lines",
        name = "Historical", line = list(color = "#1a237e", width = 2)
      ) %>%
      add_trace(
        x = fc_dates, y = as.numeric(fc$mean),
        type = "scatter", mode = "lines",
        name = "Forecast", line = list(color = "#ff9800", width = 2, dash = "dash")
      ) %>%
      add_trace(
        x = c(fc_dates, rev(fc_dates)),
        y = c(as.numeric(fc$upper[, 1]), rev(as.numeric(fc$lower[, 1]))),
        type = "scatter", mode = "lines",
        fill = "toself", fillcolor = "rgba(255,152,0,0.15)",
        line = list(color = "transparent"),
        name = paste0(input$fc_confidence, "% CI"),
        showlegend = TRUE
      )

    p %>% layout(
      title = list(
        text = paste(res$ticker, "-", toupper(res$model_type), "Forecast"),
        font = list(size = 15)
      ),
      xaxis = list(title = "Date"),
      yaxis = list(title = "Price ($)"),
      hovermode = "x unified",
      legend = list(orientation = "h", y = -0.15)
    )
  })

  output$fc_model_summary <- renderPrint({
    res <- forecast_result()
    if (is.null(res)) {
      cat("Click 'Run Forecast' to generate a forecast.")
    } else {
      summary(res$model)
    }
  })

  output$fc_residuals <- renderPlotly({
    res <- forecast_result()
    if (is.null(res)) return(plotly_empty())

    resid <- residuals(res$model)
    plot_ly(x = seq_along(resid), y = as.numeric(resid),
            type = "scatter", mode = "lines",
            line = list(color = "#78909c", width = 1),
            name = "Residuals") %>%
      layout(
        title = list(text = "Model Residuals", font = list(size = 14)),
        xaxis = list(title = "Observation"),
        yaxis = list(title = "Residual"),
        shapes = list(
          list(type = "line", x0 = 0, x1 = length(resid),
               y0 = 0, y1 = 0,
               line = list(color = "red", width = 1, dash = "dash"))
        )
      )
  })

  # ===========================================================================
  # DATA EXPLORER TAB
  # ===========================================================================
  output$data_table <- DT::renderDataTable({
    req(input$data_ticker)
    data_list <- stock_data()
    req(input$data_ticker %in% names(data_list))
    d <- data_list[[input$data_ticker]]

    df <- data.frame(
      Date = index(d),
      Open = round(as.numeric(Op(d)), 2),
      High = round(as.numeric(Hi(d)), 2),
      Low = round(as.numeric(Lo(d)), 2),
      Close = round(as.numeric(Cl(d)), 2),
      Volume = as.numeric(Vo(d)),
      stringsAsFactors = FALSE
    )
    df <- df[order(df$Date, decreasing = TRUE), ]

    DT::datatable(df, rownames = FALSE,
                  options = list(pageLength = 25, scrollX = TRUE),
                  class = "compact hover stripe") %>%
      DT::formatCurrency(c("Open", "High", "Low", "Close"), "$") %>%
      DT::formatRound("Volume", digits = 0)
  })

  output$download_csv <- downloadHandler(
    filename = function() {
      paste0(input$data_ticker, "_", Sys.Date(), ".csv")
    },
    content = function(file) {
      data_list <- stock_data()
      req(input$data_ticker %in% names(data_list))
      d <- data_list[[input$data_ticker]]
      df <- data.frame(
        Date = index(d),
        Open = as.numeric(Op(d)),
        High = as.numeric(Hi(d)),
        Low = as.numeric(Lo(d)),
        Close = as.numeric(Cl(d)),
        Volume = as.numeric(Vo(d))
      )
      write.csv(df, file, row.names = FALSE)
    }
  )

  # ===========================================================================
  # AI INSIGHTS TAB
  # ===========================================================================
  ai_summary_text <- reactiveVal(NULL)

  get_ai_config <- reactive({
    list(
      provider = input$ai_provider,
      api_key  = if (!is.null(input$openai_key)) input$openai_key else AI_DEFAULTS$openai_key,
      model    = if (input$ai_provider == "openai") input$openai_model else input$bedrock_model,
      region   = if (!is.null(input$bedrock_region)) input$bedrock_region else AI_DEFAULTS$bedrock_region
    )
  })

  get_data_context <- reactive({
    cat_name <- input$category
    cat_info <- STOCK_CATEGORIES[[cat_name]]
    m <- overview_metrics()
    build_data_context(cat_name, cat_info, m, input$date_range)
  })

  observeEvent(input$ai_summarize, {
    cfg <- get_ai_config()
    context <- get_data_context()

    focus_prompts <- list(
      overview    = "Provide a comprehensive overview covering performance, risk, trends, and key takeaways.",
      performance = "Focus primarily on performance metrics: total returns, relative performance, and price movements.",
      risk        = "Focus primarily on risk and volatility: which stocks are most/least volatile, risk-adjusted returns, and risk factors.",
      trend       = "Focus primarily on trends and momentum: recent price movements, trend direction, and momentum indicators."
    )
    focus_text <- focus_prompts[[input$ai_summary_focus]]

    messages <- list(
      list(role = "system", content = SUMMARY_SYSTEM_PROMPT),
      list(role = "user", content = paste0(
        "Here is the current dashboard data:\n\n",
        context, "\n\n",
        "Please provide an analysis of this stock category. ", focus_text
      ))
    )

    ai_summary_text("Generating AI summary...")

    result <- call_ai(
      messages    = messages,
      provider    = cfg$provider,
      api_key     = cfg$api_key,
      model       = cfg$model,
      region      = cfg$region
    )

    if (result$success) {
      ai_summary_text(result$content)
    } else {
      ai_summary_text(paste("Error:", result$error))
    }
  })

  output$ai_summary_output <- renderUI({
    txt <- ai_summary_text()
    if (is.null(txt)) {
      div(
        style = "text-align: center; padding: 40px; color: #999;",
        icon("brain", style = "font-size: 48px; margin-bottom: 15px;"),
        h4("Click 'Summarize Dashboard' to generate an AI analysis"),
        p("The AI will analyze the current stock category data and provide insights.")
      )
    } else {
      div(class = "ai-summary-box", txt)
    }
  })

  # ===========================================================================
  # AI CHAT TAB
  # ===========================================================================
  chat_history <- reactiveVal(list())

  send_chat_message <- function(user_msg) {
    cfg <- get_ai_config()
    context <- get_data_context()

    history <- chat_history()
    history <- append(history, list(list(role = "user", content = user_msg)))
    chat_history(history)

    messages <- list(
      list(role = "system", content = paste0(
        CHAT_SYSTEM_PROMPT,
        "\n\nCurrent dashboard data context:\n", context
      ))
    )
    for (msg in history) {
      messages <- append(messages, list(list(role = msg$role, content = msg$content)))
    }

    result <- call_ai(
      messages    = messages,
      provider    = cfg$provider,
      api_key     = cfg$api_key,
      model       = cfg$model,
      region      = cfg$region
    )

    if (result$success) {
      ai_reply <- result$content
    } else {
      ai_reply <- paste("Error:", result$error)
    }

    history <- append(history, list(list(role = "assistant", content = ai_reply)))
    chat_history(history)

    updateTextInput(session, "chat_input", value = "")
  }

  observeEvent(input$chat_send, {
    req(nchar(trimws(input$chat_input)) > 0)
    send_chat_message(trimws(input$chat_input))
  })

  # Enter key to send chat
  observe({
    session$sendCustomMessage("bindEnterKey", list(
      inputId = "chat_input",
      buttonId = "chat_send"
    ))
  })

  # Suggested questions
  observeEvent(input$sq1, {
    send_chat_message("Which stock has the best risk-adjusted return?")
  })
  observeEvent(input$sq2, {
    send_chat_message("Compare the volatility of the top 3 performers")
  })
  observeEvent(input$sq3, {
    send_chat_message("What trends do you see in the recent 3 months?")
  })
  observeEvent(input$sq4, {
    send_chat_message("Which stocks are most correlated?")
  })
  observeEvent(input$sq5, {
    send_chat_message("Summarize the overall sector performance")
  })
  observeEvent(input$sq6, {
    send_chat_message("What are the key risks in this category?")
  })

  observeEvent(input$chat_clear, {
    chat_history(list())
  })

  output$chat_history_ui <- renderUI({
    history <- chat_history()
    if (length(history) == 0) {
      return(div(
        class = "chat-container",
        div(
          style = "text-align: center; padding: 60px 20px; color: #999;",
          icon("comments", style = "font-size: 48px; margin-bottom: 15px;"),
          h4("Ask a question about your stock data"),
          p("The AI assistant has access to the current category's performance metrics."),
          p("Try one of the suggested questions below, or type your own.")
        )
      ))
    }

    msg_tags <- lapply(history, function(msg) {
      if (msg$role == "user") {
        div(style = "display: flex; justify-content: flex-end;",
          div(class = "chat-msg chat-msg-user",
            div(class = "chat-msg-label", "You"),
            msg$content
          )
        )
      } else {
        div(style = "display: flex; justify-content: flex-start;",
          div(class = "chat-msg chat-msg-ai",
            div(class = "chat-msg-label", "AI Assistant"),
            msg$content
          )
        )
      }
    })

    do.call(
      div,
      c(list(class = "chat-container", id = "chat-scroll-container"), msg_tags)
    )
  })
}

# ---------------------------------------------------------------------------
# Utility: Basic moment calculations (avoid extra dependency)
# ---------------------------------------------------------------------------
moments_skewness <- function(x) {
  x <- x[!is.na(x)]
  n <- length(x)
  m <- mean(x)
  s <- sqrt(sum((x - m)^2) / n)
  if (s == 0) return(0)
  (sum((x - m)^3) / n) / s^3
}

moments_kurtosis <- function(x) {
  x <- x[!is.na(x)]
  n <- length(x)
  m <- mean(x)
  s <- sqrt(sum((x - m)^2) / n)
  if (s == 0) return(0)
  (sum((x - m)^4) / n) / s^4
}

# ---------------------------------------------------------------------------
# Run the app
# ---------------------------------------------------------------------------
shinyApp(ui = ui, server = server)
