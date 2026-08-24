import streamlit as st
import base64
import os

def get_base64_video(video_path: str):
    paths_to_check = [video_path, "assetsbackground.mp4"]
    for path in paths_to_check:
        if os.path.exists(path):
            try:
                with open(path, "rb") as video_file:
                    return base64.b64encode(video_file.read()).decode("utf-8")
            except Exception as e:
                print(f"Error loading video {path}: {e}")
                
    print(f"Reminder: Drop your looping .mp4 background video into {video_path}")
    return None

def apply_glass_theme(video_path="assets/background.mp4"):
    video_base64 = get_base64_video(video_path)
    
    video_html = ""
    if video_base64:
        video_html = f"""
        <video autoplay loop muted playsinline id="bg-video">
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
        </video>
        """
    else:
        # Fallback dark gradient if video fails
        video_html = """
        <style>
        .stApp {
            background: linear-gradient(135deg, #0b0c10, #1f2833) !important;
        }
        </style>
        """

    css = f"""
    {video_html}
    <style>
    /* Fullscreen Background Video */
    #bg-video {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        object-fit: cover;
        z-index: -10;
        pointer-events: none;
        filter: brightness(0.75) saturate(1.1);
    }}

    /* Transparent Streamlit App Canvas */
    .stApp {{
        background: transparent !important;
    }}

    /* Bento-Style Frosted Glass Cards */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(20, 20, 28, 0.55) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 22px !important;
        box-shadow: 0 16px 40px 0 rgba(0, 0, 0, 0.45) !important;
        padding: 1.25rem !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }}

    /* Sleek Card Hover State */
    [data-testid="stVerticalBlockBorderWrapper"]:hover {{
        background: rgba(28, 28, 38, 0.65) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        transform: translateY(-3px) !important;
        box-shadow: 0 20px 48px 0 rgba(0, 0, 0, 0.65) !important;
    }}

    /* Frosted Glass Sidebar */
    [data-testid="stSidebar"] {{
        background: rgba(15, 16, 22, 0.75) !important;
        backdrop-filter: blur(28px) !important;
        -webkit-backdrop-filter: blur(28px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }}
    
    /* New Glass Card Class */
    .glass-card {{
      width: 240px;
      height: 360px;
      background: rgba(255, 255, 255, 0.33);
      backdrop-filter: blur(26px);
      -webkit-backdrop-filter: blur(26px);
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.3);
      box-shadow: 
        0 8px 32px rgba(0, 0, 0, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.5),
        inset 0 -1px 0 rgba(255, 255, 255, 0.1),
        inset 0 0 18px 9px rgba(255, 255, 255, 0.9);
      position: relative;
      overflow: hidden;
    }}

    .glass-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.8),
        transparent
      );
    }}

    .glass-card::after {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 1px;
      height: 100%;
      background: linear-gradient(
        180deg,
        rgba(255, 255, 255, 0.8),
        transparent,
        rgba(255, 255, 255, 0.3)
      );
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
