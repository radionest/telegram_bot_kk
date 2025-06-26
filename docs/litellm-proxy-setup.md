# LiteLLM Proxy Configuration

## Overview

The LiteLLM client supports configuring individual proxy servers for each AI model/provider. This allows:
- Using different proxies for different providers
- Bypassing regional restrictions
- Working with corporate proxies
- Load balancing across proxy servers

## Configuration

### Per-Model Proxy Settings

Add a `proxy` field to any model configuration in `litellm_models.yaml`:

```yaml
models:
  - provider: gemini
    model_name: gemini-2.0-flash-001
    api_key: your_api_key
    proxy: http://proxy.example.com:8080
    
  - provider: openai
    model_name: gpt-4
    api_key: your_api_key
    proxy: socks5://user:pass@socks-proxy.com:1080
```

### Supported Proxy Formats

1. **HTTP/HTTPS Proxy**
   ```yaml
   proxy: http://proxy.example.com:8080
   proxy: https://secure-proxy.example.com:8443
   ```

2. **SOCKS5 Proxy**
   ```yaml
   proxy: socks5://proxy.example.com:1080
   proxy: socks5://user:password@proxy.example.com:1080
   ```

3. **Environment Variables**
   ```yaml
   proxy: ${COMPANY_PROXY}
   proxy: ${GEMINI_PROXY_URL}
   ```

## How It Works

1. Each model can have its own proxy configuration
2. The proxy is applied only for requests to that specific model
3. Original proxy settings are preserved and restored after each request
4. No global proxy configuration is affected

## Example Scenarios

### Different Proxies for Different Providers

```yaml
models:
  # US proxy for OpenAI
  - provider: openai
    model_name: gpt-4
    api_key: ${OPENAI_KEY}
    proxy: http://us-proxy.company.com:3128
    
  # EU proxy for Anthropic
  - provider: anthropic
    model_name: claude-3-opus-20240229
    api_key: ${ANTHROPIC_KEY}
    proxy: http://eu-proxy.company.com:3128
    
  # No proxy for local/internal models
  - provider: ollama
    model_name: llama2
    api_base: http://localhost:11434
```

### Fallback Models with Different Proxies

```yaml
models:
  # Primary model with fast proxy
  - provider: gemini
    model_name: gemini-2.0-flash-001
    priority: 10
    proxy: http://premium-proxy.com:8080
    
  # Fallback model with free proxy
  - provider: gemini
    model_name: gemini-2.0-flash-001
    priority: 5
    proxy: http://free-proxy.com:3128
    tags: ["fallback"]
```

## Troubleshooting

1. **Proxy Connection Errors**: Check proxy URL format and credentials
2. **SSL Errors**: Some proxies may require SSL verification to be disabled
3. **Timeout Issues**: Increase the `timeout` parameter for slow proxies
4. **Authentication**: Ensure credentials are properly URL-encoded

## Security Considerations

- Store proxy credentials in environment variables, not in plain text
- Use HTTPS proxies when possible for encrypted communication
- Regularly rotate proxy credentials
- Monitor proxy usage for unusual activity