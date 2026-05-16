# ---------------------------------------------------------------------------
# AI Module - OpenAI & AWS Bedrock Integration
#
# Provides helper functions for calling LLM APIs (OpenAI, AWS Bedrock)
# to generate dashboard summaries and answer user questions about stock data.
# ---------------------------------------------------------------------------

library(httr)
library(jsonlite)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via environment variables)
# ---------------------------------------------------------------------------
AI_DEFAULTS <- list(
  provider       = Sys.getenv("AI_PROVIDER", "openai"),
  openai_key     = Sys.getenv("OPENAI_API_KEY", ""),
  openai_model   = Sys.getenv("OPENAI_MODEL", "gpt-4o"),
  openai_url     = Sys.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions"),
  bedrock_region = Sys.getenv("AWS_REGION", "us-east-1"),
  bedrock_model  = Sys.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
  max_tokens     = as.integer(Sys.getenv("AI_MAX_TOKENS", "1024")),
  temperature    = as.numeric(Sys.getenv("AI_TEMPERATURE", "0.3"))
)

# ---------------------------------------------------------------------------
# OpenAI API call
# ---------------------------------------------------------------------------
call_openai <- function(messages, api_key, model = AI_DEFAULTS$openai_model,
                        api_url = AI_DEFAULTS$openai_url,
                        max_tokens = AI_DEFAULTS$max_tokens,
                        temperature = AI_DEFAULTS$temperature) {
  if (is.null(api_key) || nchar(trimws(api_key)) == 0) {
    return(list(success = FALSE, error = "OpenAI API key is not configured."))
  }

  body <- list(
    model       = model,
    messages    = messages,
    max_tokens  = max_tokens,
    temperature = temperature
  )

  resp <- tryCatch({
    POST(
      url    = api_url,
      add_headers(
        Authorization  = paste("Bearer", api_key),
        `Content-Type` = "application/json"
      ),
      body   = toJSON(body, auto_unbox = TRUE),
      encode = "raw",
      timeout(60)
    )
  }, error = function(e) {
    return(list(success = FALSE, error = paste("HTTP error:", e$message)))
  })

  if (inherits(resp, "list") && !is.null(resp$error)) return(resp)

  if (status_code(resp) != 200) {
    err_body <- content(resp, as = "text", encoding = "UTF-8")
    return(list(success = FALSE, error = paste("API error", status_code(resp), ":", err_body)))
  }

  parsed <- fromJSON(content(resp, as = "text", encoding = "UTF-8"), simplifyVector = FALSE)
  reply <- parsed$choices[[1]]$message$content

  list(success = TRUE, content = reply)
}

# ---------------------------------------------------------------------------
# AWS Bedrock API call (Converse API via SigV4 signed request)
# ---------------------------------------------------------------------------
call_bedrock <- function(messages, model_id = AI_DEFAULTS$bedrock_model,
                         region = AI_DEFAULTS$bedrock_region,
                         max_tokens = AI_DEFAULTS$max_tokens,
                         temperature = AI_DEFAULTS$temperature) {

  access_key <- Sys.getenv("AWS_ACCESS_KEY_ID", "")
  secret_key <- Sys.getenv("AWS_SECRET_ACCESS_KEY", "")
  session_token <- Sys.getenv("AWS_SESSION_TOKEN", "")

  if (nchar(trimws(access_key)) == 0 || nchar(trimws(secret_key)) == 0) {
    return(list(success = FALSE, error = "AWS credentials are not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."))
  }

  bedrock_messages <- lapply(messages, function(m) {
    if (m$role == "system") return(NULL)
    list(
      role    = m$role,
      content = list(list(text = m$content))
    )
  })
  bedrock_messages <- Filter(Negate(is.null), bedrock_messages)

  system_msgs <- Filter(function(m) m$role == "system", messages)
  system_list <- if (length(system_msgs) > 0) {
    list(list(text = system_msgs[[1]]$content))
  } else {
    list()
  }

  body <- list(
    modelId  = model_id,
    messages = bedrock_messages,
    inferenceConfig = list(
      maxTokens   = max_tokens,
      temperature = temperature
    )
  )
  if (length(system_list) > 0) body$system <- system_list

  endpoint <- paste0("https://bedrock-runtime.", region, ".amazonaws.com")
  path <- paste0("/model/", URLencode(model_id, reserved = TRUE), "/converse")
  url <- paste0(endpoint, path)

  body_json <- toJSON(body, auto_unbox = TRUE)

  now <- Sys.time()
  timestamp <- format(now, "%Y%m%dT%H%M%SZ", tz = "UTC")
  datestamp <- format(now, "%Y%m%d", tz = "UTC")
  host <- paste0("bedrock-runtime.", region, ".amazonaws.com")

  payload_hash <- digest::digest(body_json, algo = "sha256", serialize = FALSE)

  canonical_headers <- paste0("content-type:application/json\nhost:", host, "\nx-amz-date:", timestamp, "\n")
  signed_headers <- "content-type;host;x-amz-date"

  if (nchar(session_token) > 0) {
    canonical_headers <- paste0("content-type:application/json\nhost:", host,
                                "\nx-amz-date:", timestamp,
                                "\nx-amz-security-token:", session_token, "\n")
    signed_headers <- "content-type;host;x-amz-date;x-amz-security-token"
  }

  canonical_request <- paste0(
    "POST\n", path, "\n\n",
    canonical_headers, "\n",
    signed_headers, "\n",
    payload_hash
  )

  credential_scope <- paste0(datestamp, "/", region, "/bedrock/aws4_request")
  string_to_sign <- paste0(
    "AWS4-HMAC-SHA256\n",
    timestamp, "\n",
    credential_scope, "\n",
    digest::digest(canonical_request, algo = "sha256", serialize = FALSE)
  )

  sign_hmac <- function(key, msg) {
    digest::hmac(key, msg, algo = "sha256", raw = TRUE)
  }

  k_date    <- sign_hmac(chartr("", "", paste0("AWS4", secret_key)), datestamp)
  k_region  <- sign_hmac(k_date, region)
  k_service <- sign_hmac(k_region, "bedrock")
  k_signing <- sign_hmac(k_service, "aws4_request")

  signature <- digest::hmac(k_signing, string_to_sign, algo = "sha256")

  auth_header <- paste0(
    "AWS4-HMAC-SHA256 Credential=", access_key, "/", credential_scope,
    ", SignedHeaders=", signed_headers,
    ", Signature=", signature
  )

  headers_list <- c(
    Authorization    = auth_header,
    `Content-Type`   = "application/json",
    `x-amz-date`    = timestamp
  )
  if (nchar(session_token) > 0) {
    headers_list <- c(headers_list, `x-amz-security-token` = session_token)
  }

  resp <- tryCatch({
    POST(
      url    = url,
      do.call(add_headers, as.list(headers_list)),
      body   = body_json,
      encode = "raw",
      timeout(60)
    )
  }, error = function(e) {
    return(list(success = FALSE, error = paste("HTTP error:", e$message)))
  })

  if (inherits(resp, "list") && !is.null(resp$error)) return(resp)

  if (status_code(resp) != 200) {
    err_body <- content(resp, as = "text", encoding = "UTF-8")
    return(list(success = FALSE, error = paste("Bedrock API error", status_code(resp), ":", err_body)))
  }

  parsed <- fromJSON(content(resp, as = "text", encoding = "UTF-8"), simplifyVector = FALSE)
  reply <- parsed$output$message$content[[1]]$text

  list(success = TRUE, content = reply)
}

# ---------------------------------------------------------------------------
# Unified dispatch: call the configured provider
# ---------------------------------------------------------------------------
call_ai <- function(messages, provider = NULL, api_key = NULL, model = NULL,
                    api_url = NULL, region = NULL, max_tokens = NULL,
                    temperature = NULL) {

  provider    <- provider    %||% AI_DEFAULTS$provider
  max_tokens  <- max_tokens  %||% AI_DEFAULTS$max_tokens
  temperature <- temperature %||% AI_DEFAULTS$temperature


  if (tolower(provider) == "openai") {
    api_key <- api_key %||% AI_DEFAULTS$openai_key
    model   <- model   %||% AI_DEFAULTS$openai_model
    api_url <- api_url %||% AI_DEFAULTS$openai_url
    call_openai(messages, api_key = api_key, model = model, api_url = api_url,
                max_tokens = max_tokens, temperature = temperature)
  } else if (tolower(provider) == "bedrock") {
    model  <- model  %||% AI_DEFAULTS$bedrock_model
    region <- region %||% AI_DEFAULTS$bedrock_region
    call_bedrock(messages, model_id = model, region = region,
                 max_tokens = max_tokens, temperature = temperature)
  } else {
    list(success = FALSE, error = paste("Unknown AI provider:", provider))
  }
}

# ---------------------------------------------------------------------------
# Build a context string from current dashboard data
# ---------------------------------------------------------------------------
build_data_context <- function(category_name, category_info, metrics_df,
                               date_range = NULL) {
  lines <- c(
    paste0("Stock Category: ", category_name),
    paste0("Description: ", category_info$description),
    paste0("Stocks: ", paste(category_info$tickers, collapse = ", "))
  )

  if (!is.null(date_range)) {
    lines <- c(lines, paste0("Analysis Period: ", date_range[1], " to ", date_range[2]))
  }

  if (!is.null(metrics_df) && nrow(metrics_df) > 0) {
    lines <- c(lines, "", "Performance Metrics:")
    lines <- c(lines, "Ticker | Start Price | Current Price | Total Return (%) | Ann. Volatility (%)")
    lines <- c(lines, "-------|------------|--------------|-----------------|-------------------")
    for (i in seq_len(nrow(metrics_df))) {
      r <- metrics_df[i, ]
      lines <- c(lines, paste(r$Ticker, r$StartPrice, r$EndPrice,
                               r$TotalReturn, r$AnnVolatility, sep = " | "))
    }

    avg_ret <- round(mean(metrics_df$TotalReturn, na.rm = TRUE), 1)
    avg_vol <- round(mean(metrics_df$AnnVolatility, na.rm = TRUE), 1)
    best <- metrics_df[which.max(metrics_df$TotalReturn), ]
    worst <- metrics_df[which.min(metrics_df$TotalReturn), ]

    lines <- c(lines, "",
      paste0("Average Total Return: ", avg_ret, "%"),
      paste0("Average Annualized Volatility: ", avg_vol, "%"),
      paste0("Best Performer: ", best$Ticker, " (", best$TotalReturn, "%)"),
      paste0("Worst Performer: ", worst$Ticker, " (", worst$TotalReturn, "%)")
    )
  }

  paste(lines, collapse = "\n")
}

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
SUMMARY_SYSTEM_PROMPT <- paste(
  "You are a financial analyst AI assistant integrated into a stock market dashboard.",
  "Your role is to analyze stock market data and provide clear, insightful summaries.",
  "Focus on key trends, notable performers, risk levels, and actionable insights.",
  "Use bullet points and clear formatting. Keep summaries concise but comprehensive.",
  "Always include: 1) Overall category performance, 2) Top/bottom performers with context,",
  "3) Volatility and risk assessment, 4) Key trends or patterns, 5) Brief forward-looking commentary.",
  "Do not provide specific investment advice. Use phrases like 'the data suggests' rather than 'you should buy/sell'."
)

CHAT_SYSTEM_PROMPT <- paste(
  "You are a financial analyst AI assistant integrated into a stock market dashboard.",
  "You help users understand stock market data, trends, and analysis.",
  "You have access to the current dashboard data provided in the context.",
  "Answer questions accurately based on the data. If you don't have enough information,",
  "say so. Do not fabricate data points. Keep answers focused and practical.",
  "Do not provide specific investment advice. Use data-driven language."
)

# ---------------------------------------------------------------------------
# Null-coalescing operator (if not already defined)
# ---------------------------------------------------------------------------
if (!exists("%||%")) {
  `%||%` <- function(a, b) if (is.null(a)) b else a
}
