# OpenAI API Configuration Guide

## Environment Variables

Add these variables to your `.env` file to configure OpenAI API behavior:

### Required
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Optional (with defaults)
```bash
# Rate limiting configuration
OPENAI_RATE_LIMIT=50          # Max API calls per minute (default: 50)
OPENAI_MAX_RETRIES=5          # Max retry attempts for failed calls (default: 5)
OPENAI_BASE_DELAY=1.0         # Base delay in seconds for exponential backoff (default: 1.0)
```

## Rate Limiting Features

### 1. **Automatic Rate Limiting**
- Prevents hitting OpenAI's rate limits (429 errors)
- Configurable calls per minute
- Automatic queuing when limits are reached

### 2. **Smart Retry Logic**
- Handles different error types differently:
  - **429 (Rate Limit)**: Exponential backoff with jitter
  - **Quota Exceeded**: Immediate failure (no retry)
  - **Timeouts**: Shorter backoff strategy
  - **Other Errors**: Standard exponential backoff

### 3. **Error Handling**
- **Rate Limits**: Automatically retries with increasing delays
- **Quota Issues**: Clear error messages about billing
- **Network Issues**: Graceful degradation

## Usage Examples

### Basic Usage
```python
from services.llm.utils import safe_openai_call, client

# This automatically handles rate limiting and retries
response = await safe_openai_call(
    client.chat.completions.create,
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### With Retry Decorator
```python
from services.llm.utils import retry_with_backoff

@retry_with_backoff
async def my_openai_call():
    return await client.chat.completions.create(...)
```

## Troubleshooting

### Common Issues

1. **"OpenAI quota exceeded"**
   - Check your OpenAI billing plan
   - Upgrade your plan if needed
   - Monitor usage in OpenAI dashboard

2. **Rate limit warnings**
   - Reduce `OPENAI_RATE_LIMIT` value
   - Increase delays between calls
   - Check for burst requests

3. **High retry counts**
   - Increase `OPENAI_MAX_RETRIES`
   - Check network stability
   - Verify API key validity

### Monitoring

The system logs all rate limiting and retry attempts:
- Rate limit hits
- Retry attempts and delays
- Quota exceeded errors
- Successful API calls

## Best Practices

1. **Start Conservative**: Begin with `OPENAI_RATE_LIMIT=30` and increase gradually
2. **Monitor Logs**: Watch for rate limit warnings in your application logs
3. **Plan for Growth**: Adjust limits based on your expected usage patterns
4. **Error Handling**: Always handle quota exceeded errors gracefully in your UI
