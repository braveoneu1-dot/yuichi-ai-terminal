import streamlit as st

def premium_card(title, value, subtitle="", accent="#60A5FA"):

    st.markdown(
        f"""
        <div style="
            background:#151A23;
            border:1px solid #232B38;
            border-radius:18px;
            padding:20px;
        ">
            <h5 style="
                color:#94A3B8;
                margin:0;
            ">
                {title}
            </h5>

            <h2 style="
                color:white;
                margin-top:10px;
                margin-bottom:10px;
            ">
                {value}
            </h2>

            <span style="
                color:{accent};
            ">
                {subtitle}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )