# LLM API Issues and Solutions

## Current Issues

### 1. Anthropic API Key Invalid
**Error**: `401 Unauthorized - invalid x-api-key`

**Problem**: The Anthropic API key in the `.env` file is invalid or expired.

**Solution**: 
1. Get a new API key from [Anthropic Console](https://console.anthropic.com/)
2. Update the `.env` file with the new key:
   ```
   ANTHROPIC_API_KEY=your_new_api_key_here
   ```

### 2. Gemini Content Policy Violations
**Error**: `Empty response from Gemini API - possible content policy violation`

**Problem**: The evaluation prompts are triggering Gemini's safety filters, likely due to:
- References to "evaluation" or "assessment" 
- Content that might be interpreted as educational testing
- Prompts that could be seen as potentially harmful

**Solutions**:

#### Option A: Modify Prompts (Recommended)
Update the prompt templates to be less likely to trigger content filters:

1. **Avoid trigger words**: Replace "evaluation" with "analysis", "assessment" with "review"
2. **Use neutral language**: Focus on "learning progress" rather than "performance evaluation"
3. **Add context**: Include educational context to make the purpose clear

#### Option B: Adjust Gemini Configuration
Modify the LLM settings to use different models or parameters:

```json
{
  "google": {
    "default_model": "gemini-1.5-pro",  // Try different model
    "temperature": 0.1,  // Lower temperature for more conservative responses
    "safety_settings": {
      "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
      "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
      "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
      "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
    }
  }
}
```

#### Option C: Disable Gemini as Primary Provider
Update the fallback configuration to use OpenAI as primary:

```json
{
  "fallback_configuration": {
    "fallback_order": ["openai", "anthropic", "google"]
  }
}
```

### 3. OpenAI Working Correctly
**Status**: ✅ Working as fallback provider
**Note**: This is why evaluations are still completing successfully

## Immediate Actions

### 1. Fix Anthropic API Key
```bash
# Get new API key from Anthropic Console
# Update .env file
ANTHROPIC_API_KEY=sk-ant-api03-your-new-key-here
```

### 2. Test API Connections
```python
# Test each provider individually
from src.llm_client import LLMClient
from src.config_manager import ConfigManager

config = ConfigManager()
client = LLMClient(config)

# Test each provider
print("Anthropic:", client.test_connection("anthropic"))
print("OpenAI:", client.test_connection("openai"))
print("Google:", client.test_connection("google"))
```

### 3. Update Fallback Order (Temporary Fix)
Modify `config/llm_settings.json`:

```json
{
  "fallback_configuration": {
    "fallback_order": ["openai", "anthropic", "google"]
  }
}
```

## Long-term Solutions

### 1. Prompt Engineering
- Review all prompt templates for potential trigger words
- Add educational context to make purpose clear
- Use more neutral language for evaluation tasks

### 2. Provider Diversity
- Ensure multiple working providers for redundancy
- Regular testing of API connections
- Cost monitoring across providers

### 3. Error Handling Improvements
- Better retry logic for transient failures
- More detailed error logging
- Graceful degradation when providers fail

## Testing the Fixes

After implementing fixes:

1. **Restart the application**
2. **Run a test evaluation**
3. **Check logs for API call success**
4. **Verify all evaluation phases complete**

## Cost Considerations

Current working configuration:
- **Primary**: OpenAI (GPT-4o-mini) - $0.00015/$0.0006 per 1K tokens
- **Fallback**: Anthropic (Claude) - $0.003/$0.015 per 1K tokens  
- **Last Resort**: Google (Gemini) - $0.00015/$0.0006 per 1K tokens

OpenAI is currently the most cost-effective option while working reliably. 