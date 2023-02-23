# import torch
import streamlit as st
import translators as ts
import translators.server as tss

# Locally hardcoded selection with DeepL and Google
from utils import avail_transl, lang_map, biogpt_models



def get_langs(langmap, transl_choice):
    translator_langs = langmap[transl_choice.lower()]
    return translator_langs

def get_default_outlang_index(transl_choice):
    default_out = [lang for lang in enumerate(lang_map[transl_choice.lower()]) if lang[1] == "en" ][0]
    default_out_index = int(default_out[0])
    return default_out_index

def check_input(in_text):
    in_text_length = len(in_text)
    # base warning
    # st.warning("Even though the translator API supports 5000 max chars, BioGPT limits input prompt to 2048", icon="🔥")
    
    if in_text_length == 0:
        return c2.warning(
            "Please enter some text and use CTL+Enter to confirm!", icon="🔥"
        )
    elif in_text_length > 2048 :
        return c2.error("Input text prompt must be less than 2048 characters long")
    else:
        return c2.markdown(":green[OK, ready to translate!]")

def translate_query(in_text, translator, lang_in, lang_out):
    
    out_text = ts.translate_text(in_text, translator, lang_in, lang_out)
    return out_text

def disable_form():
    st.session_state["disabled"] = True
    return st.session_state["disabled"]
    


def check_min_max_seq_compatibility(min_slider_val, max_slider_val):
    if min_slider_val > max_slider_val:
        return st.error("Enter a minimum sequence length smaller than the maximum sequence length", icon="🚨")
    # else:
    #     return st.markdown(":green[Good to go!]")
    
def generate_text(model, min_seq_len, max_seq_len, num_seq, in_text):
    pass

# st app 
st.set_page_config(layout="wide")
# Main title
st.markdown(
    "<h1 align='center'>Biomedical literature helper with BioGPT language model</h1><br>",
    unsafe_allow_html=True
)

# Translate input section
st.title("Text translation (optional)")

transl_exp = st.expander(label="Use a translator if input text in a language other than English 👇", expanded=True)
c1, c2, = transl_exp.columns((1,1.5))

with transl_exp:
    c1.subheader("Translation parameters")
    
    # Choose translator
    c1.radio(
        "Select a translator",
        options=avail_transl,
        horizontal=True,
        index=1,
        key="transl_choice",
    )
    c1.markdown("<br>**Select languages**", unsafe_allow_html=True)
    # Automatic lang finder    
    c1.checkbox("Find language automatically", key="auto_lang")

    # Input lang selection base on translator choice
    c1.selectbox(
        "Select the input language (accronym)",
        get_langs(lang_map, st.session_state["transl_choice"]),
        disabled=st.session_state["auto_lang"],
        key="transl_lang_in"
    )
    
    # Output lang selection based on translator choice
    default_index = get_default_outlang_index(st.session_state["transl_choice"].lower())
    c1.selectbox(
        "Select the output language (Default = English)",
        get_langs(lang_map, st.session_state["transl_choice"]),
        disabled=st.session_state["auto_lang"],
        index=default_index,
        key="transl_lang_out"
    )
    # Check for similar in/out for lang
    if st.session_state["transl_lang_in"] == st.session_state["transl_lang_out"]:
        c1.error("Please select two different languages for translation!", icon="🚨")
    
    ###-----------Col2----------###
    c2.subheader("Text input and output")
    # Get input for translation
    c2.text_area(
        "Input text",
        max_chars=2049,
        placeholder="Enter the text you want to translate here",
        key="transl_in_text"
    )
    check_input(st.session_state["transl_in_text"])   # warning + error
    
    ###---On left col (with syntax is sequential)---###
    clear_disabled = True
    if st.session_state["transl_in_text"] != "":
        clear_disabled = False 
    
    c1.button("Reset values/app", disabled=clear_disabled, key="clear_button")
    
    if st.session_state["clear_button"]:
        st.experimental_rerun()
    ###---end reset page---###
    
    # Output translate components    
    
    c2.button("Translate", key="translate_button")
    
    c2.markdown("---")
    
    # Title output translate
    if not st.session_state["auto_lang"]:
        c2.markdown(
            f"**Translated output from {st.session_state['transl_lang_in'].upper()} to {st.session_state['transl_lang_out'].upper()}**"
            )
    else:
        c2.write(f"**Translated output to English with automatic detection**")

    # Translate action        
    if st.session_state["translate_button"]:
        if st.session_state["auto_lang"]:
            transl_out_text = ts.translate_text(
                query_text=st.session_state["transl_in_text"],
                translator=st.session_state["transl_choice"].lower()
            )
        else:
            transl_out_text = translate_query(
                st.session_state["transl_in_text"],
                st.session_state["transl_choice"].lower(),
                st.session_state["transl_lang_in"],
                st.session_state["transl_lang_out"],
            )
    # Awaiting translate action or output        
    if not st.session_state["translate_button"]:
        c2.code(f"\nAwaiting translation...\n"
        )
    else:
        c2.code(transl_out_text)

###------BioGPT SECTION------###
st.title("BioGPT : biomedical text generation and mining")

# Left col = params / right col = gpt output
biogpt_cont = st.container()
c1, c2 = biogpt_cont.columns((1,2))

with biogpt_cont:
    model_params = c1.form(key="biogpt_form")
    with model_params:
        model_choice = st.selectbox("Select the pre-trained model", biogpt_models)
        min_slider = st.slider(
            label="Minimum sequence output length",
            min_value=25,
            max_value=250,
            value=50,
            step=5,
            help="Capped between 25-250 seq len for usability"
        )
        max_slider = st.slider(
            label="Max sequence output length",
            min_value=50,
            max_value=500,
            value=250,
            step=5,
            help="Use a max sequence > than min sequence"
        )
        num_seq_slider = st.slider(
            label="Number of returned sequences",
            min_value=1,
            max_value=5,
            value=1,
            step=1
        )
        
        # len_answer_slider = st.slider
        if "disabled" not in st.session_state:
            st.session_state["disabled"] = False
        submit_params = st.form_submit_button(
            "Generate text",
            type="primary",
            on_click=disable_form,
            disabled=st.session_state["disabled"]
        )
        check_min_max_seq_compatibility(min_slider_val=min_slider, max_slider_val=max_slider)
        # Check min_max params comptability
        if submit_params:
            # check_min_max_seq_compatibility(min_slider_val=min_slider, max_slider_val=max_slider)
            st.info(
                f"Generating text(s) sequence(s) ({min_slider} - {max_slider} characters) using {model_choice}..."
            )
        
        # Input output generation
            

st.write(st.session_state)
