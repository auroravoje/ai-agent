# AI Dinner Planning Agent 🍲

An intelligent dinner planning agent built with Azure AI Foundry and Streamlit. This application helps users plan their meals by leveraging AI to suggest recipes and manage dinner history based on user's own data and personal preferences.

## Features

- 🤖 **AI-Powered Chat Interface**: Interactive conversation with an AI agent for dinner planning, shopping list creation and emailing both to preferred addresses
- 📒 **Recipe Viewer**: Browse available recipes and view dinner history
- 🔄 **Session Management**: Reset conversations and cleanup Azure resources
- 💾 **Persistent Chat History**: Conversations are maintained across reruns within app session
- 🎨 **Custom Styling**: UI with custom background and blur effects

## Tech Stack

- **Frontend**: Streamlit
- **AI/ML**: Azure AI Foundry (AI Agents)
- **Authentication**: Azure Identity (DefaultAzureCredential)
- **Data Processing**: Pandas
- **Environment Management**: python-dotenv

## Prerequisites

- Python 3.11.9+
- Azure subscription with Microsoft AI Foundry access
- Azure AI project configured
- Email agent defined in the Azure AI project (SDK approach for email tool not working properly)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   dingen_azure_endpoint=<your-azure-ai-project-endpoint>
   email_agent_id=<your-email-agent-id>
   google_app_credentials =<path-to-your-google-credentials-json>
   google_sheet_id =<your-google-sheet-id>
   ```

4. **Set up Azure credentials**
   
   Ensure you have Azure CLI installed and authenticated:
   ```bash
   az login
   ```

## Usage

Run the application locally:

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## Project Structure

```
ai-agent/
├── app.py                 # Main application entry point
├── chat_utils.py          # Chat interaction utilities
├── agent_utils.py         # Azure AI agent management
├── data_utils.py          # Recipe data preparation
├── cleanup_utils.py       # Resource cleanup utilities
├── utils.py               # General utility functions
├── streamlit_styles.py    # Custom UI styling
├── README.md              # Project documentation
└── .env                   # Environment configuration (not in repo)
```

## Key Components

### Chat System
- **initialize_chat_history()**: Sets up chat history in session state
- **handle_user_input()**: Processes user messages and fetches AI responses
- **display_chat_history()**: Renders conversation history
- **reset_conversation()**: Clears chat state and restarts

### Agent Management
- **get_or_create_agent()**: Retrieves existing agent or creates new one
- Manages agent lifecycle and configuration

### Data Management
- **prepare_recipe_data()**: Loads and processes recipe and dinner history data
- Returns DataFrames for recipes, history, and combined data

## Deployment

For production deployment:

1. Configure Azure credentials for the deployment environment
2. Deploy using your preferred method (Azure App Service, Container, etc.)

## Planned Features

Future enhancements under consideration:

- [ ] Agentic dinner history data update
- [ ] Enhanced recipe filtering and search
- [ ] Voice interaction support

## Contributing

This is a private project. If you're interested in the approach or have suggestions, feel free to reach out via the contact information below.

## License

[Add your license here]

## Contact

For questions or feedback, please open an issue on this repository or reach out via my GitHub profile.

## Acknowledgments

- Azure AI Foundry team for the AI Agents SDK
- Streamlit community for the excellent framework
