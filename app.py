import streamlit as st
import awesome_streamlit as ast

st.set_page_config(page_title='CPR')

import app_en
import app_fr

st.markdown(f"""
    <style>
        .reportview-container .main .block-container{{
            max-width: 1280px;
            padding-top: 0em;
        }}
    </style>
    """, unsafe_allow_html=True)

st.markdown(f"""
    <style>
        .tooltip {{
            position: relative;
            display: inline-block;
            border-bottom: 1px dotted black;
        }}
        
        .tooltip .tooltiptext {{
            visibility: hidden;
            width: 120px;
            background-color: black;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 5px 0;
            /* Position the tooltip */
            position: absolute;
            z-index: 1;
            top: 100%;
            left: 50%;
            margin-left: -60px;
        }}
        
        .tooltip:hover .tooltiptext {{
            visibility: visible;
        }}
    </style>
    """, unsafe_allow_html=True)

st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)

PAGES = {
	"English": app_en,
	"Français": app_fr,
}

def main():
	st.sidebar.markdown("# Select Language")
	selection = st.sidebar.radio(" ", list(PAGES.keys()))

	page = PAGES[selection]

	with st.spinner(f"Loading {selection}..."):
		ast.shared.components.write_page(page)

if __name__ == "__main__":
	main()