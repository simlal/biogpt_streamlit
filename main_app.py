import torch
from transformers import pipeline, set_seed
from transformers import BioGptTokenizer, BioGptForCausalLM

import streamlit as st
import translators as ts
import asyncio
import datetime
import pandas as pd

# Locally hardcoded selection with DeepL and Google
from utils import avail_transl, lang_map, biogpt_models, examples



def get_langs(langmap, transl_choice):
    translator_langs = langmap[transl_choice.lower()]
    return translator_langs

def get_default_outlang_index(transl_choice):
    default_out = [lang for lang in enumerate(lang_map[transl_choice.lower()]) if lang[1] == "en" ][0]
    default_out_index = int(default_out[0])
    return default_out_index

def check_input_transl(in_text):
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
    
def check_input_predict(submit_state=False):
    if not submit_state:
        if st.session_state["pred_in_text"] is None:
            c1.warning("Make sure you have some text either from translator or manually added", icon="🔥")
    else:
        if st.session_state["pred_in_text"] is None or st.session_state["pred_in_text"] == "":
            c1.error("Make sure you have some input for text generation", icon="🚨")
            st.stop()
    
def setup_model(model_choice):
    model_dict = {
        "BioGPT" : "microsoft/biogpt",
        "BioGPT-Large" : "microsoft/BioGPT-Large",
        "BioGPT-Large-PubMedQA" : "microsoft/BioGPT-Large-PubMedQA"
    }
    model_choice = model_dict[model_choice]
    
    tokenizer = BioGptTokenizer.from_pretrained(model_choice)
    model = BioGptForCausalLM.from_pretrained(model_choice)
    return tokenizer, model

async def generate_text_from_model(model_choice, min_seq_val, max_seq_val, num_seq_val, input_text):
    with st.spinner("In progress..."):
        start = datetime.datetime.now()
        tokenizer, model = setup_model(model_choice)
        inputs = tokenizer(input_text, return_tensors="pt")
        
        set_seed(42)
        
        with torch.no_grad():
            beam_outputs = model.generate(**inputs,
                                        min_length=min_seq_val,
                                        max_length=max_seq_val,
                                        num_beams=5,
                                        num_return_sequences=num_seq_val,
                                        early_stopping=True
                                        )
        decoded_outputs =[{i: tokenizer.decode(beam_output, skip_special_tokens=True)} for i, beam_output in enumerate(beam_outputs)]
        end = datetime.datetime.now()
        time_diff = end - start
        return decoded_outputs, time_diff.seconds

#! STOPWATCH TO TIME FUNCT
# async def watch():
#     with c2.empty():
#         now = 0
#         while True: 
#             st.markdown(
#                 f"<p style='color:grey'>Generating text output...<strong>(Elapsed time = {now} seconds)</strong></p>",
#                 unsafe_allow_html=True
#             )
#             await asyncio.sleep(1)
#             now += 1
#             if stop_generate:
#                 break

#!DEPRECATED                     
# async def call_watch_predict():
#     # all_tasks = set()
#     now = 0
#     done_loop = False
#     task1 = asyncio.create_task(watch(now, done_loop))
#     task2 = asyncio.create_task(generate_text_from_model(
#         model_choice=model_choice,
#         min_seq_val=min_slider,
#         max_seq_val=max_slider,
#         num_seq_val=num_seq_slider,
#         input_text=st.session_state["pred_in_text"],
#     ))
#     # await task1
#     await task2
#         done_loop = True
#         task1.cancel()
#     return task2.result()



####---------------------STREAMLIT---------------------####

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
    c1.checkbox("Find language automatically", key="auto_lang", value=False)

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
    check_input_transl(st.session_state["transl_in_text"])   # warning + error
    
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
    if "transl_out_text" not in st.session_state:
        st.session_state["transl_out_text"] = None
    
    if st.session_state["translate_button"]:
        if st.session_state["auto_lang"]:
            st.session_state["transl_out_text"] = ts.translate_text(
                query_text=st.session_state["transl_in_text"],
                translator=st.session_state["transl_choice"].lower()
            )
        else:
            st.session_state["transl_out_text"] = translate_query(
                st.session_state["transl_in_text"],
                st.session_state["transl_choice"].lower(),
                st.session_state["transl_lang_in"],
                st.session_state["transl_lang_out"],
            )
    # Awaiting translate action or output        
    if not st.session_state["translate_button"]:
        placeholder_out_transl = c2.code(
            body="Awaiting translation...",
            language=None    
        )
        st.session_state["transl_out_text"] = None
    else:
        c2.code(st.session_state["transl_out_text"], language=None)

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
            max_value=2048,
            value=500,
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
        # Input/output section
        c2.markdown("#### Input")
        # Initialize session state with same key as txt area
        if "pred_in_text" not in st.session_state:
                st.session_state["pred_in_text"] = None
        
        # Checkbox validation to get translation output
        c2.checkbox("Use output from translation", value=True, key="predict_transl_out_check")
        if not st.session_state["predict_transl_out_check"]:
            c2.text_area(
                label=f"Enter text here for generation with {model_choice}",
                placeholder="Covid is", 
                key="pred_in_text"
            )
        else:       
            if st.session_state["transl_out_text"] is None:
                c2.warning("If checking this option, make sure to perform translation before", icon="🔥")
            else:
                c2.code(st.session_state["transl_out_text"], language=None)
                st.session_state["pred_in_text"] = st.session_state["transl_out_text"]
                
        
        # Disable on submit for generate button
        if "disabled" not in st.session_state:
            st.session_state["disabled"] = False
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            submit_params = st.form_submit_button(
                "Generate text",
                type="primary",
                on_click=disable_form,
                disabled=st.session_state["disabled"],
                help="Reload the page for a another prompt"
            )
        with subcol2:
            stop_generate = st.form_submit_button(
                "Stop generation",
                type="secondary",
                disabled=not st.session_state["disabled"]
                )
        # Check min_max params comptability for size
        check_min_max_seq_compatibility(min_slider_val=min_slider, max_slider_val=max_slider)
        check_input_predict(submit_state=False)
        
        # Output generation
        c2.markdown("---")
        c2.markdown("#### Output")   
        
        
        if not submit_params:
            c2.code(body="...", language=None)
        else:
            # Input checkpoint to avoid querying the model
            check_input_predict(submit_state=True)
            
            # Placeholders and timewatchwhile generating
            c1.info(f"Generating text(s) sequence(s) (length between {min_slider} and {max_slider}) using {model_choice}...")
            decoded_outputs, total_time = asyncio.run(generate_text_from_model(
                model_choice=model_choice,
                min_seq_val=min_slider,
                max_seq_val=max_slider,
                num_seq_val=num_seq_slider,
                input_text=st.session_state["pred_in_text"]
            ))
            # decoded_output to screen
            for output in decoded_outputs:
                for num_answer, op in output.items():    
                    c2.markdown(
                        f"""
                        <p style='font-size:20px'>
                            <span style='color:grey'><strong>Answer #{num_answer + 1} :</span>
                            <span style='color:#4295f5'>{op}</strong></span>
                        </p>
                        """,
                        unsafe_allow_html=True
                    )
            # Time to complete
            c2.markdown(
                f"<p style='color:grey'>Generated text output in <strong>{total_time} seconds</strong></p>",
                unsafe_allow_html=True
            )
df_ex = pd.DataFrame.from_dict(
    examples, orient="index", columns=[
        "Prompt", "min_seq_len", "max_seq_len", "num_seq_returned", "Model", "Output"
        ]
    )
st.markdown("<br><br>", unsafe_allow_html=True)
styles = [{'selector': 'tr:hover', 'props': [('background-color', '#848fc0')]}]
st.markdown(df_ex.style.set_table_styles(styles).to_html(), unsafe_allow_html=True)