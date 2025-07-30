# Educational Evaluator v16

An AI-powered educational evaluation system that assesses learner responses and provides detailed feedback with intelligent scoring and progress tracking.

## Features

- 🤖 **Multi-LLM Support**: Uses Anthropic Claude, OpenAI GPT-4, and Google Gemini
- 📊 **Intelligent Scoring**: Advanced evaluation algorithms with skill mastery tracking
- 📈 **Progress Tracking**: Learner history and trend analysis
- 🎯 **Activity Management**: Multiple activity types (CR, RP, BR, SR)
- 💰 **Cost Tracking**: Real-time token usage and cost estimation
- 🔄 **Fallback System**: Automatic provider switching if one fails

## Quick Start

### 1. Prerequisites
- Python 3.8 or higher
- API keys for at least one LLM provider

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd evaluator_v16

# Run the setup script (recommended)
python setup.py

# Or install dependencies manually
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the project root:
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

### 4. Run the Application
```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## API Keys Required

You need at least one of these API keys:

- **Anthropic Claude**: [Get key here](https://console.anthropic.com/)
- **OpenAI GPT-4**: [Get key here](https://platform.openai.com/)
- **Google Gemini**: [Get key here](https://aistudio.google.com/)

## Project Structure

```
evaluator_v16/
├── app.py                 # Main Streamlit application
├── src/                   # Core modules
│   ├── llm_client.py     # Multi-provider LLM client
│   ├── evaluation_pipeline.py  # Evaluation orchestration
│   ├── scoring_engine.py # Scoring algorithms
│   └── ...
├── config/               # Configuration files
├── data/                 # Database and activity data
├── schemas/              # Data schemas
└── requirements.txt      # Python dependencies
```

## Usage

1. **Select a Learner**: Choose from existing learners or create a new one
2. **Choose an Activity**: Pick from available activities (CR, RP, BR, SR types)
3. **Run Evaluation**: The system will:
   - Process the learner's response
   - Evaluate against skill criteria
   - Generate detailed feedback
   - Update progress tracking
4. **View Results**: See scoring, feedback, and summary metrics

## Features in Detail

### Evaluation Summary Card
- ⏱️ **Time Elapsed**: Total evaluation time
- 📥 **Input Tokens**: Tokens used for prompts
- 📤 **Output Tokens**: Tokens in responses
- 💰 **Estimated Cost**: Based on current API rates

### Multi-Provider Fallback
The system automatically tries providers in order:
1. Primary provider (configurable)
2. Fallback providers if primary fails
3. Cost-optimized provider selection

### Intelligent Feedback
- Context-aware feedback generation
- Skill-specific recommendations
- Progress-based suggestions

## Configuration

Key configuration files in `config/`:
- `llm_settings.json`: LLM provider preferences
- `scoring_config.json`: Scoring algorithms
- `domain_model.json`: Domain-specific settings
- `app_state.json`: Application state

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your API keys are valid and have sufficient credits
2. **Import Errors**: Make sure all dependencies are installed: `pip install -r requirements.txt`
3. **Database Issues**: The SQLite database will be created automatically in `data/`

### Logs
Check the logs in `data/logs/` for detailed error information.

## Development

### Adding New Activities
1. Create activity JSON in `data/activities/`
2. Follow the schema in `schemas/current_activity_generation_schema.md`

### Customizing Scoring
Modify `config/scoring_config.json` to adjust scoring algorithms.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here] 