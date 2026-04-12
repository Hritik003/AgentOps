# Module 1: Talk to the Machine

**Build your first LLM-powered chat application**

---

## What You'll Learn

- Set up and configure an OpenAI-compatible client
- Make inference calls to a language model
- Build an interactive chat loop with conversation history
- Handle responses and errors gracefully

---

## Prerequisites

- Python 3.10+
- API credentials (provided during workshop)

---

## Quick Start

### 1. Navigate to the module directory

```bash
cd module-01
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Create a `.env` file with your credentials:

```env
OPENAI_BASE_URL=<your-api-endpoint>
OPENAI_API_KEY=<your-api-key>
```

### 5. Run the notebook

Open `chat-app.ipynb` and follow the step-by-step instructions.

---

## Files in This Module

| File | Description |
|------|-------------|
| `chat-app.ipynb` | Step-by-step notebook with the chat application |
| `requirements.txt` | Python dependencies |
| `.env` | Your API credentials (create this) |

---

## Key Concepts

### The Chat Completions API

```python
response = client.chat.completions.create(
    model="model-name",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    max_tokens=500
)
```

### Message Roles

- `system` - Sets the assistant's behavior
- `user` - Your input/questions
- `assistant` - The model's responses

### Conversation History

To have multi-turn conversations, maintain a list of messages and append each exchange:

```python
messages = []
messages.append({"role": "user", "content": "Hi"})
# ... get response ...
messages.append({"role": "assistant", "content": response})
messages.append({"role": "user", "content": "Follow up question"})
```

---

## Next Module

Once you've completed this module, move on to:

**Module 2: Extending the Brain** - Build and deploy your own MCP Server

```bash
git checkout module-2
```
