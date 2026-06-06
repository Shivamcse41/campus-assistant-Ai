import os
import gradio as gr
from smart_rag import smart_query

# Configure environment variables (using PYTHONUTF8=1 is recommended for Windows)
os.environ["PYTHONUTF8"] = "1"

# --- Premium Custom CSS (Charcoal, Gold, Cream theme) ---
CUSTOM_CSS = """
body {
    background-color: #121212 !important;
    font-family: 'Outfit', 'Inter', sans-serif !important;
}
.gradio-container {
    background-color: #151515 !important;
    border: 1px solid #d4af37 !important;
    border-radius: 16px !important;
    padding: 30px !important;
    max-width: 1100px !important;
    margin: 40px auto !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important;
}
.premium-header {
    text-align: center;
    margin-bottom: 30px;
    border-bottom: 1px solid rgba(212, 175, 55, 0.2);
    padding-bottom: 20px;
}
.premium-title {
    color: #fffdd0 !important; /* Cream color */
    font-size: 2.8em !important;
    font-weight: 800 !important;
    letter-spacing: 2px !important;
    margin: 0 !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.6);
}
.premium-subtitle {
    color: #d4af37 !important; /* Gold color */
    font-size: 1.1em !important;
    font-weight: 500 !important;
    margin-top: 5px !important;
    letter-spacing: 1px !important;
}
.sidebar-panel {
    background-color: #1a1a1a !important;
    border: 1px solid rgba(212, 175, 55, 0.15) !important;
    border-radius: 12px !important;
    padding: 20px !important;
}
.sidebar-title {
    color: #d4af37 !important;
    font-size: 1.2em !important;
    font-weight: 700 !important;
    margin-bottom: 15px !important;
    border-bottom: 1px solid rgba(212, 175, 55, 0.2) !important;
    padding-bottom: 8px !important;
}
.info-card {
    background-color: #222222 !important;
    border-left: 3px solid #d4af37 !important;
    border-radius: 4px !important;
    padding: 10px 15px !important;
    margin-bottom: 15px !important;
    color: #fffdd0 !important;
    font-size: 0.9em !important;
}
.shortcut-btn {
    background-color: #222222 !important;
    color: #fffdd0 !important;
    border: 1px solid rgba(212, 175, 55, 0.3) !important;
    border-radius: 8px !important;
    padding: 10px !important;
    text-align: left !important;
    font-size: 0.9em !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
    margin-bottom: 8px !important;
}
.shortcut-btn:hover {
    background-color: #d4af37 !important;
    color: #121212 !important;
    border-color: #d4af37 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(212, 175, 55, 0.25) !important;
}
.chatbot-panel {
    background-color: #1a1a1a !important;
    border: 1px solid rgba(212, 175, 55, 0.15) !important;
    border-radius: 12px !important;
    padding: 20px !important;
}
.gr-button-primary {
    background: linear-gradient(135deg, #d4af37, #aa820a) !important;
    color: #121212 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}
.gr-button-primary:hover {
    background: linear-gradient(135deg, #ffe066, #d4af37) !important;
    box-shadow: 0 0 15px rgba(212, 175, 55, 0.4) !important;
    transform: translateY(-1px) !important;
}
.clear-btn {
    background-color: #222222 !important;
    color: #ff5555 !important;
    border: 1px solid rgba(255, 85, 85, 0.3) !important;
    font-weight: 600 !important;
}
.clear-btn:hover {
    background-color: #ff5555 !important;
    color: #ffffff !important;
    border-color: #ff5555 !important;
}
"""

def process_chat(message: str, history: list) -> str:
    """
    RAG Chat processor. Takes user input and history, runs smart RAG pipeline,
    and returns the formatted answer including its source.
    """
    if not message.strip():
        return ""
    
    try:
        # Run through the 3-phase smart RAG pipeline
        result = smart_query(message)
        answer = result["answer"]
        source = result["source"]
        
        # Format response with clean markdown and source block
        formatted_response = f"{answer}\n\n---\n🌐 **Source:** *{source}*"
        return formatted_response
    except Exception as e:
        return f"⚠️ **Error running query:** {str(e)}"

# Define theme colors and fonts
theme = gr.themes.Soft(
    primary_hue="amber",
    secondary_hue="stone",
    neutral_hue="zinc",
    font=[gr.themes.GoogleFont("Outfit"), "sans-serif"]
).set(
    body_background_fill="#121212",
    block_background_fill="#1a1a1a",
    block_border_color="#d4af37",
    button_primary_background_fill="*primary_500",
    button_primary_text_color="#121212"
)

# Build the layout
with gr.Blocks(title="CampConnect Navigator") as demo:
    
    # Premium Header
    gr.HTML(
        """
        <div class="premium-header">
            <h1 class="premium-title">🎓 CAMPCONNECT</h1>
            <p class="premium-subtitle">RAG-Powered Smart Campus Navigator • GP Aurangabad</p>
        </div>
        """
    )
    
    with gr.Row():
        # Left Column - Info & Quick Shortcuts
        with gr.Column(scale=1, elem_classes="sidebar-panel"):
            gr.HTML('<h3 class="sidebar-title">⚙️ Campus Info Hub</h3>')
            
            gr.HTML(
                """
                <div class="info-card">
                    ℹ️ <strong>Direct Live Connection</strong><br>
                    Connected to GP Aurangabad Vector Store and official website database.
                </div>
                """
            )
            
            gr.HTML('<h4 style="color: #fffdd0; margin-bottom: 10px; font-weight:600;">💡 Quick Query Suggestions</h4>')
            
            # Suggestion buttons
            s1 = gr.Button("What is the admission process?", elem_classes="shortcut-btn")
            s2 = gr.Button("Latest notices kya hai?", elem_classes="shortcut-btn")
            s3 = gr.Button("Tell me about civil engineering", elem_classes="shortcut-btn")
            s4 = gr.Button("How is the central library facility?", elem_classes="shortcut-btn")
            s5 = gr.Button("Hostel accommodation process", elem_classes="shortcut-btn")
            
        # Right Column - Chat Interface
        with gr.Column(scale=2, elem_classes="chatbot-panel"):
            chatbot = gr.Chatbot(height=450, show_label=False, render_markdown=True)
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ask anything about the campus...",
                    scale=4,
                    show_label=False,
                    container=False
                )
                submit = gr.Button("Submit", variant="primary", scale=1)
                
            with gr.Row():
                clear = gr.Button("Clear Chat History", elem_classes="clear-btn")

    # Connect Chat handlers
    def user_msg(user_message, history):
        if not user_message.strip():
            return "", history
        return "", history + [{"role": "user", "content": user_message}]

    def bot_msg(history):
        if not history:
            return history
        user_message = history[-1]["content"]
        response = process_chat(user_message, history[:-1])
        history.append({"role": "assistant", "content": response})
        return history

    # Submit handlers
    msg.submit(user_msg, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot_msg, chatbot, chatbot
    )
    submit.click(user_msg, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot_msg, chatbot, chatbot
    )
    
    # Clear handler
    def clear_chat():
        return []
    clear.click(clear_chat, None, chatbot)

    # Shortcut click handler
    def shortcut_click(btn_text, history):
        # 1. Add user message
        new_history = history + [{"role": "user", "content": btn_text}]
        # 2. Add empty/placeholder bot reply or immediately compute
        response = process_chat(btn_text, history)
        new_history.append({"role": "assistant", "content": response})
        return new_history

    s1.click(shortcut_click, [s1, chatbot], chatbot)
    s2.click(shortcut_click, [s2, chatbot], chatbot)
    s3.click(shortcut_click, [s3, chatbot], chatbot)
    s4.click(shortcut_click, [s4, chatbot], chatbot)
    s5.click(shortcut_click, [s5, chatbot], chatbot)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=theme, css=CUSTOM_CSS)
