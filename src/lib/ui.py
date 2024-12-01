import streamlit as st


def display_waiting_indicator():
    st.markdown(
        """
        <style>
        .typing-indicator {
            display: flex;
            align-items: center;
            height: 20px;
        }
        .typing-indicator span {
            display: inline-block;
            width: 5px;
            height: 5px;
            margin: 0 2px;
            background: #999;
            border-radius: 50%;
            animation: bounce 1s infinite alternate;
        }
        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes bounce {
            from { transform: translateY(0); }
            to { transform: translateY(-15px); }
        }
        </style>
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    """,
        unsafe_allow_html=True,
    )


def show_singular_or_plural(count: int, label: str):
    return f"{count} {label}" if count == 1 else f"{count} {label}s"
